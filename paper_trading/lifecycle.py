"""Sprint 33.7: derive a coherent paper-trade lifecycle from Atlas state."""
from __future__ import annotations

LIFECYCLE_STAGES = (
    ("Find", "Find Opportunity"),
    ("Analyse", "Analyse"),
    ("Plan", "Plan"),
    ("Ready", "Readiness"),
    ("Position", "Paper Position"),
    ("Exit", "Completed Trade"),
    ("Review", "Review"),
    ("Learn", "Atlas Learns"),
)


def lifecycle_state(*, has_scan=False, has_analysis=False, has_plan=False,
                    readiness_status=None, has_open_position=False,
                    has_completed_trade=False, has_review=False,
                    has_learning=False):
    """Return ordered lifecycle stages and the next useful action.

    The lifecycle is descriptive UI state only. It never places, blocks, or
    resizes an order.
    """
    readiness = str(readiness_status or "").strip().lower()
    ready_complete = readiness in {"ready", "caution"}
    flags = (
        bool(has_scan), bool(has_analysis), bool(has_plan), ready_complete,
        bool(has_open_position), bool(has_completed_trade), bool(has_review),
        bool(has_learning),
    )
    stages = [
        {"key": key, "label": label, "complete": complete}
        for (key, label), complete in zip(LIFECYCLE_STAGES, flags)
    ]
    completed = sum(int(s["complete"]) for s in stages)
    next_stage = next((s for s in stages if not s["complete"]), None)
    return {
        "stages": stages,
        "completed": completed,
        "total": len(stages),
        "pct": completed / len(stages),
        "next_stage": next_stage["label"] if next_stage else "Cycle complete",
    }


def lifecycle_text(state):
    """Compact text suitable for a Streamlit lifecycle strip."""
    return "  →  ".join(
        ("✓ " if stage["complete"] else "○ ") + stage["label"]
        for stage in state["stages"]
    )
