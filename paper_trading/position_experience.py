"""Position-level context helpers for Sprint 34.1 portfolio UX."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class PositionExperience:
    status: str
    status_detail: str
    stop_price: float | None
    target_price: float | None
    distance_to_stop_pct: float | None
    distance_to_target_pct: float | None
    reward_risk_ratio: float | None


def build_position_experience(*, entry_price: float, current_price: float,
                              stop_price: float | None = None,
                              target_price: float | None = None) -> PositionExperience:
    if entry_price <= 0 or current_price <= 0:
        raise ValueError("Entry and current prices must be greater than zero.")
    d_stop = ((current_price - stop_price) / current_price) if stop_price is not None else None
    d_target = ((target_price - current_price) / current_price) if target_price is not None else None
    rr = None
    if stop_price is not None and target_price is not None and entry_price > stop_price:
        rr = (target_price - entry_price) / (entry_price - stop_price)
    if stop_price is not None and current_price <= stop_price:
        status, detail = "Stop reached", "Price is at or below the planned stop."
    elif target_price is not None and current_price >= target_price:
        status, detail = "Target reached", "Price is at or above the planned target."
    elif stop_price is not None and d_stop is not None and d_stop <= 0.03:
        status, detail = "Near stop", "Price is within 3% of the planned stop."
    elif target_price is not None and d_target is not None and 0 <= d_target <= 0.03:
        status, detail = "Near target", "Price is within 3% of the planned target."
    elif current_price > entry_price:
        status, detail = "In profit", "Position is currently above average entry."
    elif current_price < entry_price:
        status, detail = "Under entry", "Position is currently below average entry."
    else:
        status, detail = "At entry", "Position is trading around average entry."
    return PositionExperience(status, detail, stop_price, target_price, d_stop, d_target, rr)
