"""Paper-trading workflow state and journal completeness helpers."""

from __future__ import annotations


def workflow_steps(*, has_scan, has_thesis, has_risk_plan, has_open_position,
                   has_completed_trade, has_review):
    return [
        ("Scanner", bool(has_scan)),
        ("Trade Thesis", bool(has_thesis)),
        ("Risk Plan", bool(has_risk_plan)),
        ("Paper Position", bool(has_open_position)),
        ("Completed Trade", bool(has_completed_trade)),
        ("Post-Trade Review", bool(has_review)),
    ]


def workflow_progress(**kwargs):
    steps=workflow_steps(**kwargs)
    completed=sum(1 for _,done in steps if done)
    return {
        "steps":steps,
        "completed":completed,
        "total":len(steps),
        "pct":completed/len(steps) if steps else 0.0,
    }


def review_completeness(review):
    if not review:
        return 0.0
    fields=(
        review.get("followed_plan") is not None,
        bool(str(review.get("emotional_state") or "").strip()),
        bool(str(review.get("what_worked") or "").strip()),
        bool(str(review.get("what_went_wrong") or "").strip()),
        bool(str(review.get("lesson_learned") or "").strip()),
    )
    return sum(fields)/len(fields)
