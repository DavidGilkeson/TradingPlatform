"""Pre-trade behavioural reminders derived from the trader's own journal."""

from __future__ import annotations

import pandas as pd

from .mistake_intelligence import mistake_summary, recurring_lessons


def build_behaviour_guard(mistake_frame, *, recurring_threshold=2, lesson_limit=3):
    """Create a non-binding guard from completed, reviewed paper trades.

    A pattern is considered recurring once it has reached ``recurring_threshold``
    observations. One-off mistakes are still preserved in the journal but do not
    trigger a strong pre-trade warning.
    """
    if mistake_frame is None or mistake_frame.empty:
        return {
            "level": "insufficient",
            "headline": "No behavioural evidence yet",
            "primary_mistake": None,
            "mistakes": [],
            "lessons": [],
        }

    summary = mistake_summary(mistake_frame)
    lessons = recurring_lessons(mistake_frame, limit=lesson_limit)

    if summary.empty:
        return {
            "level": "insufficient",
            "headline": "No behavioural evidence yet",
            "primary_mistake": None,
            "mistakes": [],
            "lessons": lessons,
        }

    recurring = summary[
        pd.to_numeric(summary["Occurrences"], errors="coerce")
        >= int(recurring_threshold)
    ].copy()

    if recurring.empty:
        first = summary.iloc[0].to_dict()
        return {
            "level": "early",
            "headline": "Behaviour sample is still early",
            "primary_mistake": first,
            "mistakes": summary.head(3).to_dict("records"),
            "lessons": lessons,
        }

    # mistake_summary is already sorted most-negative P&L first.
    primary = recurring.iloc[0].to_dict()
    net_pnl = float(primary.get("Net P&L") or 0.0)
    level = "caution" if net_pnl < 0 else "reminder"

    return {
        "level": level,
        "headline": (
            "Recurring behaviour risk detected"
            if level == "caution"
            else "Recurring behaviour pattern detected"
        ),
        "primary_mistake": primary,
        "mistakes": recurring.head(3).to_dict("records"),
        "lessons": lessons,
    }


def behaviour_guard_message(guard):
    primary = guard.get("primary_mistake") if guard else None
    if not primary:
        return "Atlas does not yet have enough reviewed trades for a personal behaviour warning."

    mistake = primary.get("Mistake", "Behaviour pattern")
    occurrences = int(primary.get("Occurrences", 0))
    pnl = float(primary.get("Net P&L", 0.0))
    return (
        f"Your most important current journal pattern is **{mistake}**. "
        f"It has appeared {occurrences} time(s) and is associated with "
        f"{pnl:+,.2f} paper P&L."
    )
