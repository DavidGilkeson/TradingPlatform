"""Risk planning and order validation for Atlas paper trading."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class RiskPlan:
    account_equity: float
    entry_price: float
    stop_price: float
    target_price: float | None
    risk_per_share: float
    max_risk_amount: float
    recommended_shares: int
    position_value: float
    position_pct: float
    reward_per_share: float | None
    reward_risk_ratio: float | None


@dataclass(slots=True)
class RiskDecision:
    allowed: bool
    warnings: list[str]
    blockers: list[str]


def calculate_position_size(
    *,
    account_equity: float,
    entry_price: float,
    stop_price: float,
    risk_pct: float = 1.0,
    target_price: float | None = None,
    max_position_pct: float = 20.0,
) -> RiskPlan:
    """Calculate risk-based share sizing for a long paper trade."""

    if account_equity <= 0:
        raise ValueError("Account equity must be greater than zero.")
    if entry_price <= 0 or stop_price <= 0:
        raise ValueError("Entry and stop prices must be greater than zero.")
    if stop_price >= entry_price:
        raise ValueError("For a long trade, stop price must be below entry price.")
    if risk_pct <= 0:
        raise ValueError("Risk percentage must be greater than zero.")
    if max_position_pct <= 0:
        raise ValueError("Maximum position percentage must be greater than zero.")

    risk_per_share = entry_price - stop_price
    max_risk_amount = account_equity * (risk_pct / 100.0)

    shares_by_risk = int(max_risk_amount // risk_per_share)
    max_position_value = account_equity * (max_position_pct / 100.0)
    shares_by_exposure = int(max_position_value // entry_price)

    recommended_shares = max(
        min(shares_by_risk, shares_by_exposure),
        0,
    )
    position_value = recommended_shares * entry_price
    position_pct = (
        position_value / account_equity * 100.0
        if account_equity
        else 0.0
    )

    reward_per_share = None
    reward_risk_ratio = None

    if target_price is not None:
        if target_price <= entry_price:
            raise ValueError("Target price must be above entry price.")
        reward_per_share = target_price - entry_price
        reward_risk_ratio = reward_per_share / risk_per_share

    return RiskPlan(
        account_equity=account_equity,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        risk_per_share=risk_per_share,
        max_risk_amount=max_risk_amount,
        recommended_shares=recommended_shares,
        position_value=position_value,
        position_pct=position_pct,
        reward_per_share=reward_per_share,
        reward_risk_ratio=reward_risk_ratio,
    )


def validate_order_risk(
    *,
    account_equity: float,
    cash: float,
    shares: float,
    entry_price: float,
    stop_price: float,
    risk_pct_limit: float = 1.0,
    max_position_pct: float = 20.0,
    minimum_reward_risk: float = 2.0,
    target_price: float | None = None,
) -> RiskDecision:
    """Validate a proposed long paper order against Atlas risk rules."""

    blockers: list[str] = []
    warnings: list[str] = []

    if shares <= 0:
        blockers.append("Share quantity must be greater than zero.")
        return RiskDecision(False, warnings, blockers)

    if stop_price >= entry_price:
        blockers.append("Stop-loss must be below the entry price for a long trade.")
        return RiskDecision(False, warnings, blockers)

    position_value = shares * entry_price
    trade_risk = shares * (entry_price - stop_price)

    max_risk = account_equity * risk_pct_limit / 100.0
    max_position = account_equity * max_position_pct / 100.0

    if position_value > cash:
        blockers.append("Order value exceeds available paper cash.")

    if trade_risk > max_risk:
        blockers.append(
            f"Trade risks ${trade_risk:,.2f}, above the "
            f"${max_risk:,.2f} risk limit."
        )

    if position_value > max_position:
        blockers.append(
            f"Position value ${position_value:,.2f} exceeds the "
            f"{max_position_pct:.1f}% portfolio exposure limit."
        )

    if target_price is not None:
        if target_price <= entry_price:
            blockers.append("Take-profit target must be above entry price.")
        else:
            ratio = (
                (target_price - entry_price)
                / (entry_price - stop_price)
            )
            if ratio < minimum_reward_risk:
                warnings.append(
                    f"Reward/risk is {ratio:.2f}:1, below the "
                    f"{minimum_reward_risk:.2f}:1 target."
                )
    else:
        warnings.append("No take-profit target has been set.")

    return RiskDecision(
        allowed=not blockers,
        warnings=warnings,
        blockers=blockers,
    )
