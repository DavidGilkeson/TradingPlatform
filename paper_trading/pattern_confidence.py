"""Sample-quality safeguards for Atlas paper-trading intelligence."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(slots=True)
class PatternConfidence:
    trades: int
    sample_grade: str
    evidence_level: str
    reliability_score: int
    eligible_for_insight: bool
    warning: str | None


def sample_grade(trades: int) -> str:
    """Grade a pattern by the amount of evidence behind it."""
    if trades <= 0:
        return "No Data"
    if trades < 5:
        return "Very Small"
    if trades < 10:
        return "Small"
    if trades < 20:
        return "Developing"
    if trades < 50:
        return "Useful"
    return "Strong"


def evidence_level(trades: int) -> str:
    """Human-readable evidence strength."""
    if trades < 5:
        return "Very Low"
    if trades < 10:
        return "Low"
    if trades < 20:
        return "Moderate"
    if trades < 50:
        return "Good"
    return "High"


def reliability_score(trades: int) -> int:
    """Conservative 0-100 score based only on sample size."""
    if trades <= 0:
        return 0

    # Smoothly rises with evidence and deliberately takes time to approach 100.
    score = 100 * (1 - math.exp(-trades / 25))
    return min(100, max(0, round(score)))


def assess_pattern_confidence(
    trades: int,
    *,
    minimum_evidence_trades: int = 10,
) -> PatternConfidence:
    trades = max(0, int(trades))
    eligible = trades >= int(minimum_evidence_trades)

    warning = None
    if trades == 0:
        warning = "No completed trades support this pattern."
    elif trades < 5:
        warning = (
            "Extremely small sample. One trade can materially distort the result."
        )
    elif trades < minimum_evidence_trades:
        warning = (
            f"Early signal only. Atlas requires at least "
            f"{minimum_evidence_trades} trades before promoting this pattern."
        )
    elif trades < 20:
        warning = (
            "Pattern has passed the minimum evidence threshold, but the sample "
            "is still developing."
        )

    return PatternConfidence(
        trades=trades,
        sample_grade=sample_grade(trades),
        evidence_level=evidence_level(trades),
        reliability_score=reliability_score(trades),
        eligible_for_insight=eligible,
        warning=warning,
    )


def add_sample_quality(
    frame: pd.DataFrame,
    *,
    minimum_evidence_trades: int = 10,
) -> pd.DataFrame:
    """Attach evidence-quality columns to an intelligence table."""
    if frame is None or frame.empty:
        return pd.DataFrame() if frame is None else frame.copy()

    result = frame.copy()
    assessments = [
        assess_pattern_confidence(
            int(trades),
            minimum_evidence_trades=minimum_evidence_trades,
        )
        for trades in result["Trades"]
    ]

    result["Sample Grade"] = [a.sample_grade for a in assessments]
    result["Evidence"] = [a.evidence_level for a in assessments]
    result["Reliability"] = [a.reliability_score for a in assessments]
    result["Insight Ready"] = [a.eligible_for_insight for a in assessments]
    result["Sample Warning"] = [a.warning or "" for a in assessments]

    return result


def strongest_eligible_pattern(
    labelled_frames: list[tuple[str, pd.DataFrame]],
    *,
    minimum_evidence_trades: int = 10,
) -> tuple[str, float, int] | None:
    """Return the highest-expectancy pattern with enough supporting trades."""
    candidates: list[tuple[str, float, int]] = []

    for label_column, frame in labelled_frames:
        if frame is None or frame.empty:
            continue

        quality = add_sample_quality(
            frame,
            minimum_evidence_trades=minimum_evidence_trades,
        )
        quality = quality[quality["Insight Ready"]]

        if quality.empty:
            continue

        best = quality.sort_values(
            ["Expectancy", "Trades"],
            ascending=[False, False],
        ).iloc[0]

        candidates.append(
            (
                str(best[label_column]),
                float(best["Expectancy"]),
                int(best["Trades"]),
            )
        )

    if not candidates:
        return None

    return max(candidates, key=lambda item: (item[1], item[2]))
