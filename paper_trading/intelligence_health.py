"""Consolidated health diagnostics for Atlas paper-trading intelligence."""

from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

from .account import PaperAccountService
from .outcome_calibration import calibration_summary, calibration_by_match_score
from .setup_intelligence import setup_performance, evidence_qualified_setup_leader
from .regime_intelligence import market_regime_intelligence


@dataclass(slots=True)
class IntelligenceHealth:
    score:int
    grade:str
    completed_trades:int
    calibrated_trades:int
    exact_links:int
    legacy_unlinked:int
    calibration_coverage:float
    exact_link_coverage:float
    evidence_ready_setups:int
    correlation:float|None
    status:str


def _grade(score:int)->str:
    if score>=85:return "A"
    if score>=70:return "B"
    if score>=55:return "C"
    if score>=40:return "D"
    return "Early"


def _status(score:int)->str:
    if score>=85:return "Strong evidence base"
    if score>=70:return "Healthy and developing"
    if score>=55:return "Developing evidence"
    if score>=40:return "Limited evidence"
    return "Too early to rely on heavily"


def intelligence_health(service:PaperAccountService)->IntelligenceHealth:
    account=service.active_account()
    with service.database.connect() as c:
        completed=int(c.execute(
            "SELECT COUNT(*) FROM paper_trades WHERE account_id=?",
            (account.id,)).fetchone()[0])

    cal=calibration_summary(service)
    coverage=(cal.calibrated_trades/completed) if completed else 0.0
    link_denominator=cal.exact_linked_allocations+cal.legacy_unlinked_trades
    link_coverage=(
        cal.exact_linked_allocations/link_denominator
        if link_denominator else 0.0
    )

    setups=setup_performance(
        service,
        dimensions=("Score Band","Confidence Band","Trend Regime"),
        minimum_trades=1,
        minimum_evidence_trades=10,
    )
    ready=int(setups["Insight Ready"].sum()) if not setups.empty else 0

    # Health measures data quality and evidence maturity, not profitability.
    sample_component=min(completed/50.0,1.0)*35
    calibration_component=min(coverage,1.0)*25
    linkage_component=min(link_coverage,1.0)*20
    setup_component=min(ready/5.0,1.0)*20
    score=round(sample_component+calibration_component+linkage_component+setup_component)

    return IntelligenceHealth(
        score=score,
        grade=_grade(score),
        completed_trades=completed,
        calibrated_trades=cal.calibrated_trades,
        exact_links=cal.exact_linked_allocations,
        legacy_unlinked=cal.legacy_unlinked_trades,
        calibration_coverage=coverage,
        exact_link_coverage=link_coverage,
        evidence_ready_setups=ready,
        correlation=cal.correlation,
        status=_status(score),
    )


def strongest_setup(service:PaperAccountService):
    frame=setup_performance(
        service,
        dimensions=("Score Band","Confidence Band","Trend Regime"),
        minimum_trades=1,
        minimum_evidence_trades=10,
    )
    return evidence_qualified_setup_leader(frame)


def strongest_regime(service:PaperAccountService):
    frame=market_regime_intelligence(service)
    if frame is None or frame.empty:
        return None
    ready=frame
    if "Insight Ready" in ready.columns:
        ready=ready[ready["Insight Ready"]]
    if ready.empty:
        return None
    expectancy_col=next(
        (c for c in ("Expectancy","Average P&L","Average Return") if c in ready.columns),
        None,
    )
    if expectancy_col is None:
        return None
    return ready.sort_values(expectancy_col,ascending=False).iloc[0].to_dict()


def calibration_bands(service:PaperAccountService)->pd.DataFrame:
    return calibration_by_match_score(service)
