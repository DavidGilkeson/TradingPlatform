"""Sprint 34.0: compact command-centre summaries for paper trading."""
from __future__ import annotations
from datetime import datetime, timezone


def _date_prefix(value) -> str:
    if value is None:
        return ""
    text = str(value)
    return text[:10]


def build_command_centre_summary(*, snapshot, positions, trades, today=None):
    """Return presentation-ready account and activity facts.

    Pure helper: no Streamlit side effects, so dashboard behaviour is easy to
    regression test. ``today`` is injectable for deterministic tests.
    """
    today = today or datetime.now(timezone.utc).date().isoformat()
    position_rows = list(positions or [])
    trade_rows = list(trades or [])
    invested = float(getattr(snapshot, "positions_value", 0.0) or 0.0)
    equity = float(getattr(snapshot, "equity", 0.0) or 0.0)
    cash = float(getattr(snapshot, "cash", 0.0) or 0.0)
    realised = float(getattr(snapshot, "realised_pnl", 0.0) or 0.0)
    unrealised = float(getattr(snapshot, "unrealised_pnl", 0.0) or 0.0)
    todays = [t for t in trade_rows if _date_prefix(t.get("exit_date")) == today]
    today_pnl = sum(float(t.get("realised_pnl") or 0.0) for t in todays)
    return {
        "equity": equity,
        "cash": cash,
        "invested": invested,
        "total_pnl": realised + unrealised,
        "total_return_pct": float(getattr(snapshot, "total_return_pct", 0.0) or 0.0),
        "open_positions": int(getattr(snapshot, "open_positions", len(position_rows)) or 0),
        "completed_trades": len(trade_rows),
        "today_completed_trades": len(todays),
        "today_realised_pnl": today_pnl,
        "cash_pct": (cash / equity) if equity > 0 else 0.0,
        "invested_pct": (invested / equity) if equity > 0 else 0.0,
    }


def next_action_text(lifecycle):
    next_stage = str((lifecycle or {}).get("next_stage") or "Find Opportunity")
    mapping = {
        "Find Opportunity": "Run the scanner and choose an opportunity to investigate.",
        "Analyse": "Review the Atlas analysis before planning a trade.",
        "Plan": "Write the thesis, invalidation, stop and target.",
        "Readiness": "Complete the trade-readiness checklist before buying.",
        "Paper Position": "The plan is ready; use the Trade tab when you want to place the paper order.",
        "Completed Trade": "Monitor the open paper position and follow its exit plan.",
        "Review": "Review the completed trade while the decision is still fresh.",
        "Atlas Learns": "Complete the lesson fields so Atlas can carry the evidence forward.",
        "Cycle complete": "This trade cycle is complete. Start with the next scanner opportunity.",
    }
    return mapping.get(next_stage, f"Continue with: {next_stage}.")
