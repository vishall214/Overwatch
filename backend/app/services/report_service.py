"""
OVERWATCH — Report Service
==========================
Generates periodic analytics reports, persists report artifacts,
and optionally sends them via SMTP email.
"""

import csv
import json
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Literal

from app.config import Settings
from app.database.crud import (
    get_alert_summary,
    get_alerts_over_time,
    get_event_distribution,
    get_threat_metrics,
)
from app.database.database import SessionLocal
from app.database.models import AlertRow
from app.utils.snapshot_utils import build_snapshot_url, extract_snapshot_filename

logger = logging.getLogger(__name__)

ReportPeriod = Literal["daily", "weekly"]


class ReportService:
    """Generate, store, and retrieve report artifacts."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._reports_dir = Path(settings.reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        period: ReportPeriod,
        trigger: str = "manual",
        now: datetime | None = None,
    ) -> dict:
        """Generate a report artifact for a period and return metadata."""
        if period not in {"daily", "weekly"}:
            raise ValueError("Invalid period. Use 'daily' or 'weekly'.")

        now_utc = self._to_utc(now or datetime.now(timezone.utc))
        window_hours = 24 if period == "daily" else 24 * 7
        cutoff = now_utc - timedelta(hours=window_hours)

        db = SessionLocal()
        try:
            summary = get_alert_summary(db=db, range_hours=window_hours)
            distribution = get_event_distribution(db=db, range_hours=window_hours)
            trend = get_alerts_over_time(db=db, interval="hour", range_hours=window_hours)
            threat = get_threat_metrics(db=db, range_hours=window_hours, peak_limit=10)

            rows = (
                db.query(AlertRow)
                .filter(AlertRow.timestamp >= cutoff)
                .order_by(AlertRow.timestamp.desc())
                .limit(1000)
                .all()
            )

            recent_events: list[dict] = []
            for row in rows:
                metadata = row.metadata_ or {}
                snapshot_path = str(getattr(row, "snapshot_path", "") or "")
                snapshot_filename = extract_snapshot_filename(snapshot_path)
                timestamp = getattr(row, "timestamp", None)
                recent_events.append(
                    {
                        "id": row.id,
                        "event_type": row.event_type,
                        "zone": row.zone or "",
                        "timestamp": timestamp.isoformat() if timestamp is not None else "",
                        "track_id": row.track_id,
                        "snapshot_path": snapshot_path,
                        "snapshot_filename": snapshot_filename,
                        "snapshot_url": build_snapshot_url(snapshot_filename),
                        "threat_score": int(metadata.get("threat_score", 0)),
                        "threat_level": str(metadata.get("threat_level", "LOW")),
                    }
                )
        finally:
            db.close()

        report_id = f"{period}_report_{now_utc.strftime('%Y%m%d_%H%M%S')}"
        payload = {
            "report_id": report_id,
            "period": period,
            "trigger": trigger,
            "generated_at": now_utc.isoformat(),
            "window": {
                "start": cutoff.isoformat(),
                "end": now_utc.isoformat(),
                "hours": window_hours,
            },
            "summary": summary,
            "distribution": distribution,
            "threat": threat,
            "trend": trend,
            "recent_events": recent_events,
        }

        json_path = self._reports_dir / f"{report_id}.json"
        csv_path = self._reports_dir / f"{report_id}.csv"

        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._write_csv(csv_path, recent_events)

        email_sent = False
        if self._settings.report_email_enabled:
            email_sent = self._send_report_email(payload, json_path, csv_path)

        return {
            "id": report_id,
            "period": period,
            "trigger": trigger,
            "generated_at": payload["generated_at"],
            "summary": summary,
            "files": {
                "json": json_path.name,
                "csv": csv_path.name,
            },
            "email_sent": email_sent,
        }

    def list_reports(self, limit: int = 30) -> list[dict]:
        """Return available report artifact metadata, newest first."""
        safe_limit = max(1, min(limit, 200))
        files = sorted(
            self._reports_dir.glob("*_report_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        reports: list[dict] = []
        for path in files[:safe_limit]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                report_id = str(payload.get("report_id", path.stem))
                reports.append(
                    {
                        "id": report_id,
                        "period": payload.get("period", "daily"),
                        "trigger": payload.get("trigger", "manual"),
                        "generated_at": payload.get("generated_at", ""),
                        "summary": payload.get("summary", {}),
                        "files": {
                            "json": path.name,
                            "csv": f"{path.stem}.csv",
                        },
                    }
                )
            except Exception:
                logger.exception("Failed parsing report file: %s", path)

        return reports

    def get_report(self, report_id: str) -> dict:
        """Load and return a report JSON payload by report id."""
        path = self.get_report_file_path(report_id, format_="json")
        return json.loads(path.read_text(encoding="utf-8"))

    def get_report_file_path(self, report_id: str, format_: str = "json") -> Path:
        """Resolve and validate report artifact path for download."""
        safe_report_id = self._sanitize_report_id(report_id)
        if format_ not in {"json", "csv"}:
            raise ValueError("format must be 'json' or 'csv'")

        path = self._reports_dir / f"{safe_report_id}.{format_}"
        if not path.is_file():
            raise FileNotFoundError(f"Report artifact not found: {path.name}")
        return path

    @staticmethod
    def _sanitize_report_id(report_id: str) -> str:
        clean = report_id.strip()
        if not clean:
            raise ValueError("report_id is required")

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        if any(ch not in allowed for ch in clean):
            raise ValueError("Invalid report id")

        return clean

    @staticmethod
    def _to_utc(ts: datetime) -> datetime:
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    @staticmethod
    def _write_csv(path: Path, events: list[dict]) -> None:
        """Persist a flat CSV summary for quick exports."""
        columns = [
            "id",
            "event_type",
            "zone",
            "timestamp",
            "track_id",
            "threat_score",
            "threat_level",
            "snapshot_filename",
        ]

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for event in events:
                writer.writerow({key: event.get(key, "") for key in columns})

    def _send_report_email(self, payload: dict, json_path: Path, csv_path: Path) -> bool:
        """Send generated report attachments over SMTP when configured."""
        recipients = [entry.strip() for entry in self._settings.report_email_recipients if entry.strip()]
        if not recipients:
            logger.warning("Report email enabled but no recipients configured")
            return False

        if not self._settings.smtp_host or not self._settings.smtp_from:
            logger.warning("Report email enabled but SMTP host/from not configured")
            return False

        summary = payload.get("summary", {})
        subject = f"[OVERWATCH] {payload.get('period', 'daily').title()} Report {payload.get('generated_at', '')}"

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._settings.smtp_from
        message["To"] = ", ".join(recipients)
        message.set_content(
            "\n".join(
                [
                    f"Report ID: {payload.get('report_id', '')}",
                    f"Period: {payload.get('period', '')}",
                    f"Generated At (UTC): {payload.get('generated_at', '')}",
                    "",
                    f"Total Alerts: {summary.get('total', 0)}",
                    f"Intrusion: {summary.get('intrusion', 0)}",
                    f"Loitering: {summary.get('loitering', 0)}",
                    f"Crowd: {summary.get('crowd', 0)}",
                    f"Weapon Detected: {summary.get('weapon_detected', 0)}",
                    f"Weapon In Zone: {summary.get('weapon_in_zone', 0)}",
                    f"Avg Threat: {summary.get('avg_threat_score', 0)}",
                    f"Peak Threat: {summary.get('peak_threat_score', 0)}",
                ]
            )
        )

        message.add_attachment(
            json_path.read_bytes(),
            maintype="application",
            subtype="json",
            filename=json_path.name,
        )
        if csv_path.is_file():
            message.add_attachment(
                csv_path.read_bytes(),
                maintype="text",
                subtype="csv",
                filename=csv_path.name,
            )

        try:
            with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=20) as smtp:
                if self._settings.smtp_use_tls:
                    smtp.starttls()
                if self._settings.smtp_username:
                    smtp.login(self._settings.smtp_username, self._settings.smtp_password)
                smtp.send_message(message)
            logger.info("Report email sent to %d recipients", len(recipients))
            return True
        except Exception:
            logger.exception("Failed sending report email")
            return False
