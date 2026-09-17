"""Transparent pre-trade readiness assessment for Atlas paper BUY orders."""
from __future__ import annotations


def _score_value(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def assess_trade_readiness(*, has_market_price, thesis, invalidation,
                           risk_allowed, guardrails_allowed, planned_rr,
                           minimum_rr, atlas_score=None,
                           regime_evidence="Insufficient evidence",
                           behaviour_level="insufficient", confirmed=False):
    """Return a non-predictive process-readiness score and checklist.

    Hard safety/process blockers determine Not Ready. The numeric score is a
    transparent checklist completion score; it is not a forecast of returns.
    """
    rr=_score_value(planned_rr)
    min_rr=_score_value(minimum_rr) or 0.0
    score=_score_value(atlas_score)
    regime=str(regime_evidence or "").lower()

    checks=[
        ("Valid market price", bool(has_market_price), True),
        ("Written trade thesis", bool(str(thesis or "").strip()), True),
        ("Written invalidation condition", bool(str(invalidation or "").strip()), False),
        ("Risk controls passed", bool(risk_allowed), True),
        ("Portfolio guardrails passed", bool(guardrails_allowed), True),
        (f"Reward/risk ≥ {min_rr:g}:1", rr is not None and rr >= min_rr, True),
        ("Atlas score available", score is not None, False),
        ("Regime evidence not cautionary", "caution" not in regime, False),
        ("No recurring behaviour caution", behaviour_level != "caution", False),
        ("Paper-order confirmation", bool(confirmed), True),
    ]
    completed=sum(1 for _,ok,_ in checks if ok)
    pct=round(100*completed/len(checks)) if checks else 0
    blockers=[label for label,ok,hard in checks if hard and not ok]
    cautions=[label for label,ok,hard in checks if not hard and not ok]
    if blockers:
        status="Not Ready"
    elif cautions or pct < 90:
        status="Caution"
    else:
        status="Ready"
    return {"status":status,"score":pct,"checks":checks,
            "blockers":blockers,"cautions":cautions}
