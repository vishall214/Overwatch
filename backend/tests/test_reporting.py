from app.config import Settings
from app.database.crud import create_alert_row
from app.database.database import Base, SessionLocal, engine
from app.services.report_service import ReportService
from app.utils.snapshot_utils import extract_snapshot_filename


def test_extract_snapshot_filename_handles_windows_paths() -> None:
    assert (
        extract_snapshot_filename(r"storage\snapshots\intrusion_20260401_120000.jpg")
        == "intrusion_20260401_120000.jpg"
    )
    assert (
        extract_snapshot_filename("storage/snapshots/intrusion_20260401_120000.jpg")
        == "intrusion_20260401_120000.jpg"
    )


def test_report_generation_and_listing(tmp_path) -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        create_alert_row(
            db=db,
            event_type="intrusion",
            track_id=7,
            zone="A",
            snapshot_path=r"storage\snapshots\intrusion_test.jpg",
            metadata={"threat_score": 42, "threat_level": "MEDIUM"},
        )
    finally:
        db.close()

    settings = Settings(
        reports_dir=str(tmp_path / "reports"),
        report_email_enabled=False,
    )
    service = ReportService(settings)

    artifact = service.generate_report("daily", trigger="test")
    assert artifact["id"].startswith("daily_report_")

    listed = service.list_reports(limit=20)
    assert any(entry["id"] == artifact["id"] for entry in listed)

    payload = service.get_report(artifact["id"])
    assert payload["period"] == "daily"
    assert payload["summary"]["total"] >= 1
    assert any(event.get("snapshot_filename") == "intrusion_test.jpg" for event in payload["recent_events"])

    json_path = service.get_report_file_path(artifact["id"], format_="json")
    csv_path = service.get_report_file_path(artifact["id"], format_="csv")
    assert json_path.is_file()
    assert csv_path.is_file()
