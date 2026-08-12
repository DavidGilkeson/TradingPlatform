from datetime import date
import pandas as pd

from paper_trading.portfolio_guardrails import (
    GuardrailSettings,
    _current_loss_streak,
    _daily_realised_pnl,
    validate_new_position_against_exposure,
)


def test_current_loss_streak():
    frame = pd.DataFrame(
        {
            "realised_pnl": [100, -20, -30, -40],
            "exit_date": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-04",
            ],
        }
    )
    assert _current_loss_streak(frame) == 3


def test_win_resets_loss_streak():
    frame = pd.DataFrame(
        {
            "realised_pnl": [-20, -30, 50],
            "exit_date": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
            ],
        }
    )
    assert _current_loss_streak(frame) == 0


def test_daily_realised_pnl():
    frame = pd.DataFrame(
        {
            "realised_pnl": [-100, 25, 500],
            "exit_date": [
                "2026-01-10T01:00:00+00:00",
                "2026-01-10T04:00:00+00:00",
                "2026-01-11T01:00:00+00:00",
            ],
        }
    )
    assert _daily_realised_pnl(
        frame,
        trading_date=date(2026, 1, 10),
    ) == -75


def test_projected_exposure_allowed():
    allowed, projected = validate_new_position_against_exposure(
        account_equity=10000,
        current_exposure_value=5000,
        proposed_position_value=2000,
        max_total_exposure_pct=80,
    )
    assert allowed
    assert projected == 70


def test_projected_exposure_blocked():
    allowed, projected = validate_new_position_against_exposure(
        account_equity=10000,
        current_exposure_value=7000,
        proposed_position_value=2000,
        max_total_exposure_pct=80,
    )
    assert not allowed
    assert projected == 90


def test_default_settings():
    settings = GuardrailSettings()
    assert settings.max_total_exposure_pct == 80
    assert settings.max_open_positions == 8
    assert settings.daily_loss_limit_pct == 3
    assert settings.consecutive_loss_limit == 3
