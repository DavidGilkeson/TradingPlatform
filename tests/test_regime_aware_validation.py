import pandas as pd
from paper_trading.regime_validation import (
    regime_leaders,regime_warning,regime_evidence_matrix)


def frame():
    rows=[]
    for market,vol,ret,excess in [
        ("Bullish","Normal",5,3),
        ("Bearish","Volatile",-2,-4),
    ]:
        for _ in range(6):
            rows.append({
                "market_regime":market,
                "volatility_regime":vol,
                "horizon_days":5,
                "return_pct":ret,
                "excess_return_pct":excess,
                "decision":"TAKEN",
                "atlas_score":85,
                "confidence":8,
            })
    return pd.DataFrame(rows)


def test_regime_leaders_find_best_and_worst():
    leaders=regime_leaders(frame())
    assert leaders["market"]["best"]["regime"]=="Bullish"
    assert leaders["market"]["worst"]["regime"]=="Bearish"
    assert leaders["volatility"]["best"]["regime"]=="Normal"
    assert leaders["volatility"]["worst"]["regime"]=="Volatile"


def test_regime_warning_flags_negative_edge():
    messages=regime_warning(
        frame(),market_regime="Bearish",horizon_days=5)
    assert messages[0]["level"]=="caution"
    assert "-4.00%" in messages[0]["message"]


def test_regime_warning_marks_positive_edge():
    messages=regime_warning(
        frame(),market_regime="Bullish",horizon_days=5)
    assert messages[0]["level"]=="favourable"


def test_regime_warning_requires_evidence():
    small=frame().head(2)
    messages=regime_warning(
        small,market_regime="Bullish",minimum_observations=5)
    assert messages[0]["level"]=="insufficient"


def test_regime_matrix_combines_conditions():
    matrix=regime_evidence_matrix(frame())
    bullish=matrix[
        (matrix["Market Regime"]=="Bullish")
        & (matrix["Volatility Regime"]=="Normal")
    ].iloc[0]
    assert bullish["Observations"]==6
    assert bool(bullish["Evidence Ready"]) is True
    assert bullish["Avg Excess Return"]==3
