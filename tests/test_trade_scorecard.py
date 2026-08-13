import pandas as pd
import pytest

from paper_trading.trade_scorecard import (
    _current_dimensions,
    _historical_verdict,
)


def test_current_dimensions_bands_values():
    result = _current_dimensions(
        atlas_score=94,
        confidence=9,
        trend_regime="Bullish",
        volatility_regime="Lower Volatility",
        verdict="Strong Buy",
    )
    assert result["Score Band"] == "Score 90+"
    assert result["Confidence Band"] == "Confidence 9-10"
    assert result["Trend Regime"] == "Bullish"


def test_current_dimensions_omits_missing_optional_values():
    result = _current_dimensions(
        atlas_score=85,
        confidence=None,
        trend_regime=None,
        volatility_regime=None,
        verdict=None,
    )
    assert result == {"Score Band": "Score 80-89"}


def test_favourable_verdict_requires_evidence():
    assert _historical_verdict(
        matched_trades=12,
        expectancy=50,
        win_rate=0.70,
        insight_ready=True,
    ) == "Historically favourable"


def test_positive_verdict():
    assert _historical_verdict(
        matched_trades=20,
        expectancy=25,
        win_rate=0.50,
        insight_ready=True,
    ) == "Historically positive"


def test_unfavourable_verdict():
    assert _historical_verdict(
        matched_trades=20,
        expectancy=-50,
        win_rate=0.30,
        insight_ready=True,
    ) == "Historically unfavourable"


def test_early_evidence_overrides_outcome():
    assert _historical_verdict(
        matched_trades=2,
        expectancy=500,
        win_rate=1.0,
        insight_ready=False,
    ) == "Early evidence"


def test_no_match_verdict():
    assert _historical_verdict(
        matched_trades=0,
        expectancy=None,
        win_rate=None,
        insight_ready=False,
    ) == "No historical match"
