import pandas as pd
from paper_trading.decision_support import build_decision_support


def evidence_frame(market="Bullish",vol="Normal",excess=2.0,n=6):
    return pd.DataFrame([{
        "market_regime":market,
        "volatility_regime":vol,
        "horizon_days":5,
        "return_pct":3.0,
        "excess_return_pct":excess,
        "decision":"TAKEN",
        "atlas_score":90,
        "confidence":8,
    } for _ in range(n)])


def test_favourable_overlay():
    result=build_decision_support(
        evidence_frame(),
        market_regime="Bullish",
        volatility_regime="Normal",
    )
    assert result["overall"]=="Favourable"
    assert len(result["evidence"])==2


def test_caution_overrides_positive_evidence():
    a=evidence_frame("Bullish","Normal",2.0)
    b=evidence_frame("Bearish","Volatile",-3.0)
    frame=pd.concat([a,b],ignore_index=True)
    result=build_decision_support(
        frame,market_regime="Bearish",volatility_regime="Volatile")
    assert result["overall"]=="Caution"


def test_insufficient_sample_is_not_treated_as_edge():
    result=build_decision_support(
        evidence_frame(n=2),
        market_regime="Bullish",
        volatility_regime="Normal",
    )
    assert result["overall"]=="Insufficient evidence"


def test_missing_regime_is_safe():
    result=build_decision_support(
        evidence_frame(),market_regime=None,volatility_regime=None)
    assert result["overall"]=="Insufficient evidence"
    assert result["evidence"]==[]
