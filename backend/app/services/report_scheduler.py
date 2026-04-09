"""
OVERWATCH — Report Scheduler
============================
Background scheduler for daily and weekly report generation.
"""

import logging
import threading
from datetime import date, datetime, timezone

from app.config import Settings
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


class ReportScheduler:
    """Simple UTC scheduler for periodic report generation."""

    def __init__(self, settings: Settings, report_service: ReportService) -> None:
        self._settings = settings
        self._report_service = report_service
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_daily_date: date | None = None
        self._last_weekly_key: str | None = None

    def start(self) -> None:
        """Start scheduler thread if enabled and not already running."""
        if not self._settings.report_scheduler_enabled:
            logger.info("Report scheduler disabled by configuration")
            return

        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="overwatch-report-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Report scheduler started")

    def stop(self) -> None:
        """Stop scheduler thread gracefully."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Report scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Whether scheduler thread is currently running."""
        return self._thread is not None and self._thread.is_alive()

    def get_status(self) -> dict:
        """Return scheduler runtime status and configuration."""
        hour, minute = self._parse_daily_time()
        return {
            "enabled": self._settings.report_scheduler_enabled,
            "running": self.is_running,
            "daily_time_utc": f"{hour:02d}:{minute:02d}",
            "weekly_day_utc": int(self._settings.report_weekly_day_utc),
            "poll_seconds": int(self._settings.report_scheduler_poll_seconds),
            "last_daily_date": self._last_daily_date.isoformat() if self._last_daily_date else "",
            "last_weekly_key": self._last_weekly_key or "",
            "email_enabled": bool(self._settings.report_email_enabled),
            "email_recipients_count": len(
                [entry for entry in self._settings.report_email_recipients if entry.strip()]
            ),
        }

    def _run_loop(self) -> None:
        """Scheduler worker loop."""
        while not self._stop_event.is_set():
            try:
                self._tick(datetime.now(timezone.utc))
            except Exception:
                logger.exception("Report scheduler tick failed")

            self._stop_event.wait(float(self._settings.report_scheduler_poll_seconds))

    def _tick(self, now_utc: datetime) -> None:
        """Evaluate whether scheduled reports should be generated."""
        hour, minute = self._parse_daily_time()
        reached_daily_time = now_utc.hour > hour or (
            now_utc.hour == hour and now_utc.minute >= minute
        )

        if not reached_daily_time:
            return

        today = now_utc.date()
        if self._last_daily_date != today:
            self._report_service.generate_report("daily", trigger="scheduled", now=now_utc)
            self._last_daily_date = today

        weekly_key = f"{now_utc.isocalendar().year}-W{now_utc.isocalendar().week:02d}"
        if (
            now_utc.weekday() == int(self._settings.report_weekly_day_utc)
            and self._last_weekly_key != weekly_key
        ):
            self._report_service.generate_report("weekly", trigger="scheduled", now=now_utc)
            self._last_weekly_key = weekly_key

    def _parse_daily_time(self) -> tuple[int, int]:
        """Parse configured daily HH:MM UTC time safely."""
        raw = str(self._settings.report_daily_time_utc or "").strip()
        try:
            hour_str, minute_str = raw.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except Exception:
            pass

        logger.warning(
            "Invalid report_daily_time_utc '%s'. Falling back to 23:55 UTC",
            raw,
        )
        return 23, 55
