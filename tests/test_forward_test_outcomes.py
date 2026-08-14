import pandas as pd
import pytest

from paper_trading.forward_testing import (
    ForwardTestRepository,
    ForwardTestOutcomeRepository,
    outcome_comparison,
    decision_quality,
)


def test_outcome_roundtrip_and_return(tmp_path):
    path = str(tmp_path / "forward.db")
    decisions = ForwardTestRepository(path)
    outcomes = ForwardTestOutcomeRepository(path)

    decision_id = decisions.record(
        account_id=1,
        ticker="AAPL",
        decision="TAKEN",
        market_price=100,
    )

    outcomes.save_outcome(
        forward_test_id=decision_id,
        horizon_days=5,
        observed_price=110,
    )

    frame = outcomes.outcomes(1)

    assert len(frame) == 1
    assert frame.iloc[0]["return_pct"] == pytest.approx(10.0)


def test_outcome_upsert(tmp_path):
    path = str(tmp_path / "forward.db")
    decisions = ForwardTestRepository(path)
    outcomes = ForwardTestOutcomeRepository(path)

    decision_id = decisions.record(
        account_id=1,
        ticker="AAPL",
        decision="SKIPPED",
        market_price=100,
    )

    outcomes.save_outcome(
        forward_test_id=decision_id,
        horizon_days=5,
        observed_price=105,
    )
    outcomes.save_outcome(
        forward_test_id=decision_id,
        horizon_days=5,
        observed_price=120,
    )

    frame = outcomes.outcomes(1)
    assert len(frame) == 1
    assert frame.iloc[0]["return_pct"] == pytest.approx(20.0)


def test_decision_quality():
    frame = pd.DataFrame(
        {
            "horizon_days": [5, 5, 5, 5],
            "decision": ["TAKEN", "TAKEN", "SKIPPED", "SKIPPED"],
            "return_pct": [10.0, 4.0, 2.0, -2.0],
        }
    )

    result = decision_quality(frame, 5)

    assert result["taken_average_return"] == pytest.approx(7.0)
    assert result["skipped_average_return"] == pytest.approx(0.0)
    assert result["decision_edge"] == pytest.approx(7.0)


def test_comparison_groups_horizons_and_decisions():
    frame = pd.DataFrame(
        {
            "horizon_days": [5, 5, 10],
            "decision": ["TAKEN", "SKIPPED", "TAKEN"],
            "return_pct": [5.0, -1.0, 8.0],
        }
    )

    result = outcome_comparison(frame)
    assert len(result) == 3
    assert set(result["Horizon Days"]) == {5, 10}


def test_invalid_outcome_rejected(tmp_path):
    path = str(tmp_path / "forward.db")
    decisions = ForwardTestRepository(path)
    outcomes = ForwardTestOutcomeRepository(path)

    decision_id = decisions.record(
        account_id=1,
        ticker="AAPL",
        decision="WATCH",
        market_price=100,
    )

    with pytest.raises(ValueError):
        outcomes.save_outcome(
            forward_test_id=decision_id,
            horizon_days=0,
            observed_price=100,
        )
