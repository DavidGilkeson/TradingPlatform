"""Non-binding decision support for proposed Atlas paper trades."""

from __future__ import annotations

from .regime_validation import regime_warning


def build_decision_support(
    outcomes,
    *,
    market_regime=None,
    volatility_regime=None,
    horizon_days=5,
    minimum_observations=5,
):
    evidence=regime_warning(
        outcomes,
        market_regime=market_regime,
        volatility_regime=volatility_regime,
        horizon_days=horizon_days,
        minimum_observations=minimum_observations,
    )
    levels={item["level"] for item in evidence}
    if "caution" in levels:
        overall="Caution"
    elif evidence and levels <= {"favourable"}:
        overall="Favourable"
    elif "favourable" in levels:
        overall="Mixed"
    elif "neutral" in levels:
        overall="Neutral"
    else:
        overall="Insufficient evidence"
    return {"overall":overall,"evidence":evidence}
