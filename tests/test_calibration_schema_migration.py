from paper_trading import PaperAccountService
from paper_trading.outcome_calibration import build_calibration_frame, calibration_summary

def test_calibration_creates_missing_snapshot_table(tmp_path):
    db_path = tmp_path / "legacy.db"
    service = PaperAccountService(str(db_path))
    service.initialise_account(starting_balance=10000)

    with service.database.connect() as connection:
        connection.execute("DROP TABLE IF EXISTS paper_intelligence_snapshots")

    assert build_calibration_frame(service).empty
    assert calibration_summary(service).calibrated_trades == 0

    with service.database.connect() as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='paper_intelligence_snapshots'"
        ).fetchone()

    assert row is not None
