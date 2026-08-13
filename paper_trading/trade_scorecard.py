"""Evidence-based historical setup scorecards for Atlas paper trades."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd

from .account import PaperAccountService
from .pattern_confidence import assess_pattern_confidence
from .setup_intelligence import build_setup_trade_frame, _confidence_band, _score_band


@dataclass(slots=True)
class TradeScorecard:
    match_score: int
    matched_trades: int
    wins: int
    win_rate: float | None
    expectancy: float | None
    average_return: float | None
    net_pnl: float | None
    sample_grade: str
    evidence_level: str
    reliability: int
    insight_ready: bool
    verdict: str
    matched_dimensions: tuple[str, ...]


def _normalise(value) -> str:
    return str(value or "").strip().lower()


def _current_dimensions(
    *,
    atlas_score: float | None,
    confidence: float | None,
    trend_regime: str | None,
    volatility_regime: str | None,
    verdict: str | None,
) -> dict[str, str]:
    values = {}

    if atlas_score is not None:
        values["Score Band"] = _score_band(atlas_score)

    if confidence is not None:
        values["Confidence Band"] = _confidence_band(confidence)

    if trend_regime:
        values["Trend Regime"] = str(trend_regime)

    if volatility_regime:
        values["Volatility Regime"] = str(volatility_regime)

    if verdict:
        values["Verdict"] = str(verdict).strip()

    return values


def _historical_verdict(
    *,
    matched_trades: int,
    expectancy: float | None,
    win_rate: float | None,
    insight_ready: bool,
) -> str:
    if matched_trades == 0:
        return "No historical match"

    if not insight_ready:
        return "Early evidence"

    expectancy = float(expectancy or 0)
    win_rate = float(win_rate or 0)

    if expectancy > 0 and win_rate >= 0.60:
        return "Historically favourable"

    if expectancy > 0:
        return "Historically positive"

    if expectancy < 0 and win_rate <= 0.40:
        return "Historically unfavourable"

    if expectancy < 0:
        return "Historically negative"

    return "Historically neutral"


def historical_setup_scorecard(
    service: PaperAccountService,
    *,
    db_path: str = "data/paper_trading.db",
    atlas_score: float | None = None,
    confidence: float | None = None,
    trend_regime: str | None = None,
    volatility_regime: str | None = None,
    verdict: str | None = None,
    minimum_evidence_trades: int = 10,
) -> TradeScorecard:
    """Compare a proposed setup with completed historical paper trades."""

    dimensions = _current_dimensions(
        atlas_score=atlas_score,
        confidence=confidence,
        trend_regime=trend_regime,
        volatility_regime=volatility_regime,
        verdict=verdict,
    )

    if not dimensions:
        raise ValueError("At least one current setup dimension is required.")

    frame = build_setup_trade_frame(service, db_path=db_path)

    if frame.empty:
        assessment = assess_pattern_confidence(
            0,
            minimum_evidence_trades=minimum_evidence_trades,
        )
        return TradeScorecard(
            0, 0, 0, None, None, None, None,
            assessment.sample_grade,
            assessment.evidence_level,
            assessment.reliability_score,
            assessment.eligible_for_insight,
            "No historical match",
            tuple(dimensions.keys()),
        )

    mask = pd.Series(True, index=frame.index)

    for column, value in dimensions.items():
        mask &= frame[column].map(_normalise) == _normalise(value)

    matches = frame[mask].copy()
    count = len(matches)

    assessment = assess_pattern_confidence(
        count,
        minimum_evidence_trades=minimum_evidence_trades,
    )

    if count == 0:
        return TradeScorecard(
            0, 0, 0, None, None, None, None,
            assessment.sample_grade,
            assessment.evidence_level,
            assessment.reliability_score,
            assessment.eligible_for_insight,
            "No historical match",
            tuple(dimensions.keys()),
        )

    pnl = pd.to_numeric(matches["realised_pnl"], errors="coerce").dropna()
    returns = pd.to_numeric(matches["return_pct"], errors="coerce").dropna()

    wins = int((pnl > 0).sum())
    win_rate = float((pnl > 0).mean()) if not pnl.empty else None
    expectancy = float(pnl.mean()) if not pnl.empty else None
    net_pnl = float(pnl.sum()) if not pnl.empty else None
    average_return = float(returns.mean()) if not returns.empty else None

    # Match score blends observed outcomes with evidence reliability.
    # It is deliberately capped by sample reliability so tiny samples cannot
    # produce a misleading 90-100 score.
    outcome_component = 50.0

    if win_rate is not None:
        outcome_component = win_rate * 70.0

    if expectancy is not None:
        # Smooth directional expectancy contribution; avoids dollar-scale
        # domination while preserving positive/negative evidence.
        outcome_component += 15.0 * math.tanh(expectancy / 100.0)

    outcome_component = max(0.0, min(100.0, outcome_component))
    evidence_weight = assessment.reliability_score / 100.0

    match_score = round(
        50.0 + (outcome_component - 50.0) * evidence_weight
    )
    match_score = max(0, min(100, match_score))

    return TradeScorecard(
        match_score=match_score,
        matched_trades=count,
        wins=wins,
        win_rate=win_rate,
        expectancy=expectancy,
        average_return=average_return,
        net_pnl=net_pnl,
        sample_grade=assessment.sample_grade,
        evidence_level=assessment.evidence_level,
        reliability=assessment.reliability_score,
        insight_ready=assessment.eligible_for_insight,
        verdict=_historical_verdict(
            matched_trades=count,
            expectancy=expectancy,
            win_rate=win_rate,
            insight_ready=assessment.eligible_for_insight,
        ),
        matched_dimensions=tuple(dimensions.keys()),
    )
