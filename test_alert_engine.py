"""Unit tests for Project Atlas alert generation."""

from pathlib import Path

import pandas as pd

from alert_engine import (
    generate_alerts_for_scan,
    get_alerts,
    initialise_alert_database,
    store_alerts,
)
from historical_scans import save_historical_scan


def _scan(score: float, verdict: str, rsi: float, volume: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": "TEST",
                "Close": 110.0,
                "20-Day MA": 105.0,
                "50-Day MA": 100.0,
                "Atlas Score": score,
                "Atlas Verdict": verdict,
                "Atlas Grade": "A",
                "RSI": rsi,
                "Relative Volume": volume,
                "Strength (%)": 8.0,
            }
        ]
    )


def test_alert_generation_and_persistence(tmp_path: Path) -> None:
    database_path = tmp_path / "atlas_test.db"
    initialise_alert_database(database_path)

    save_historical_scan(
        _scan(70, "WATCH", 65, 1.0),
        database_path=database_path,
    )
    second_scan_id = save_historical_scan(
        _scan(90, "STRONG BUY", 72, 2.1),
        database_path=database_path,
    )

    assert second_scan_id is not None

    alerts = generate_alerts_for_scan(
        second_scan_id,
        database_path=database_path,
    )

    alert_types = {alert["alert_type"] for alert in alerts}

    assert "score_increase" in alert_types
    assert "entered_strong_buy" in alert_types
    assert "volume_spike" in alert_types
    assert "entered_overbought" in alert_types

    inserted = store_alerts(alerts, database_path)
    assert inserted == len(alerts)

    # Idempotency: the same alerts should not be inserted twice.
    assert store_alerts(alerts, database_path) == 0

    saved = get_alerts(database_path=database_path)
    assert len(saved) == len(alerts)
