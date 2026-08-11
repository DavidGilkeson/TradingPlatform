"""One-click paper-trade intent helpers for Atlas.

Streamlit is imported lazily so core paper-trading modules remain testable
without Streamlit installed.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _session_state():
    import streamlit as st
    return st.session_state


def queue_paper_trade(
    *,
    ticker: str,
    side: str = "BUY",
    reason: str = "",
    notes: str = "",
    shares: float = 1.0,
) -> None:
    """Store a pending paper-trade intent."""

    state = _session_state()

    state["paper_trade_intent"] = {
        "ticker": str(ticker).upper().strip(),
        "side": str(side).upper().strip(),
        "reason": str(reason),
        "notes": str(notes),
        "shares": float(shares),
    }
    state["paper_trade_intent_pending"] = True


def consume_paper_trade_intent() -> dict[str, Any] | None:
    """Return the current queued trade intent."""

    state = _session_state()

    if not state.get("paper_trade_intent_pending"):
        return None

    return state.get("paper_trade_intent")


def clear_paper_trade_intent() -> None:
    """Clear the queued trade intent."""

    state = _session_state()
    state.pop("paper_trade_intent", None)
    state["paper_trade_intent_pending"] = False


def best_reason_from_row(
    row: pd.Series | dict[str, Any],
) -> str:
    """Create a concise trade reason from Atlas data."""

    data = row.to_dict() if isinstance(row, pd.Series) else dict(row)

    verdict = str(
        data.get(
            "Atlas Verdict",
            data.get("Signal", ""),
        )
    ).strip()

    score = data.get(
        "Atlas Score",
        data.get("Score"),
    )

    if verdict and score is not None:
        try:
            return f"{verdict} · Atlas Score {float(score):.1f}"
        except (TypeError, ValueError):
            return verdict

    return verdict or "Atlas opportunity"
