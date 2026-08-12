import pandas as pd

from paper_trading.setup_intelligence import (
    _confidence_band,
    _score_band,
    evidence_qualified_setup_leader,
)
from paper_trading.pattern_confidence import add_sample_quality


def test_score_bands():
    assert _score_band(95) == "Score 90+"
    assert _score_band(85) == "Score 80-89"
    assert _score_band(75) == "Score 70-79"
    assert _score_band(65) == "Score 60-69"
    assert _score_band(50) == "Score <60"


def test_confidence_bands():
    assert _confidence_band(10) == "Confidence 9-10"
    assert _confidence_band(8) == "Confidence 7-8"
    assert _confidence_band(6) == "Confidence 5-6"
    assert _confidence_band(3) == "Confidence <5"


def test_unknown_bands():
    assert _score_band(float("nan")) == "Score Unknown"
    assert _confidence_band(float("nan")) == "Confidence Unknown"


def test_setup_leader_requires_evidence():
    frame = pd.DataFrame(
        {
            "Setup": ["Lucky", "Robust"],
            "Trades": [2, 12],
            "Win_Rate": [1.0, 0.75],
            "Net_PnL": [500.0, 900.0],
            "Expectancy": [250.0, 75.0],
        }
    )
    frame = add_sample_quality(
        frame,
        minimum_evidence_trades=10,
    )

    leader = evidence_qualified_setup_leader(frame)

    assert leader is not None
    assert leader.setup == "Robust"
    assert leader.trades == 12


def test_setup_leader_prefers_expectancy_after_evidence():
    frame = pd.DataFrame(
        {
            "Setup": ["A", "B"],
            "Trades": [15, 20],
            "Win_Rate": [0.6, 0.7],
            "Net_PnL": [750.0, 800.0],
            "Expectancy": [50.0, 40.0],
        }
    )
    frame = add_sample_quality(
        frame,
        minimum_evidence_trades=10,
    )

    leader = evidence_qualified_setup_leader(frame)
    assert leader.setup == "A"


def test_no_evidence_qualified_setup():
    frame = pd.DataFrame(
        {
            "Setup": ["A"],
            "Trades": [3],
            "Win_Rate": [1.0],
            "Net_PnL": [300.0],
            "Expectancy": [100.0],
        }
    )
    frame = add_sample_quality(
        frame,
        minimum_evidence_trades=10,
    )

    assert evidence_qualified_setup_leader(frame) is None


def test_empty_setup_leader_safe():
    assert evidence_qualified_setup_leader(pd.DataFrame()) is None
