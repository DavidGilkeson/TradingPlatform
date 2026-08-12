import pandas as pd

from paper_trading.pattern_confidence import (
    add_sample_quality,
    assess_pattern_confidence,
    evidence_level,
    reliability_score,
    sample_grade,
    strongest_eligible_pattern,
)


def test_sample_grades():
    assert sample_grade(0) == "No Data"
    assert sample_grade(2) == "Very Small"
    assert sample_grade(7) == "Small"
    assert sample_grade(15) == "Developing"
    assert sample_grade(30) == "Useful"
    assert sample_grade(60) == "Strong"


def test_evidence_levels():
    assert evidence_level(2) == "Very Low"
    assert evidence_level(7) == "Low"
    assert evidence_level(15) == "Moderate"
    assert evidence_level(30) == "Good"
    assert evidence_level(60) == "High"


def test_reliability_increases_with_sample():
    assert reliability_score(2) < reliability_score(10)
    assert reliability_score(10) < reliability_score(50)


def test_small_sample_not_insight_ready():
    result = assess_pattern_confidence(
        4,
        minimum_evidence_trades=10,
    )
    assert not result.eligible_for_insight
    assert result.warning


def test_threshold_sample_is_insight_ready():
    result = assess_pattern_confidence(
        10,
        minimum_evidence_trades=10,
    )
    assert result.eligible_for_insight


def test_quality_columns_added():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "Trades": [3, 25],
            "Expectancy": [100.0, 20.0],
        }
    )
    result = add_sample_quality(
        frame,
        minimum_evidence_trades=10,
    )
    assert "Reliability" in result.columns
    assert not bool(result.iloc[0]["Insight Ready"])
    assert bool(result.iloc[1]["Insight Ready"])


def test_strongest_pattern_ignores_lucky_small_sample():
    frame = pd.DataFrame(
        {
            "ticker": ["LUCKY", "ROBUST"],
            "Trades": [2, 20],
            "Expectancy": [500.0, 50.0],
        }
    )
    result = strongest_eligible_pattern(
        [("ticker", frame)],
        minimum_evidence_trades=10,
    )
    assert result is not None
    assert result[0] == "ROBUST"


def test_no_eligible_pattern_returns_none():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "Trades": [2],
            "Expectancy": [500.0],
        }
    )
    assert strongest_eligible_pattern(
        [("ticker", frame)],
        minimum_evidence_trades=10,
    ) is None
