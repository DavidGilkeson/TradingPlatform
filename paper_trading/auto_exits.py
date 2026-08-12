"""Automatic simulated stop-loss and take-profit exits for Atlas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .account import PaperAccountService
from .exit_plans import ExitPlanRepository, evaluate_exit_plan
from .orders import PaperOrderService


@dataclass(slots=True)
class AutoExitEvent:
    ticker: str
    exit_reason: str
    trigger_price: float
    filled_price: float
    shares: float
    realised_pnl: float
    order_id: int


def evaluate_auto_exit_for_position(
    *,
    ticker: str,
    entry_price: float,
    current_price: float,
    stop_price: float | None,
    target_price: float | None,
) -> str | None:
    """Return STOP_LOSS, TAKE_PROFIT, or None for the current price."""

    status = evaluate_exit_plan(
        ticker=ticker,
        entry_price=entry_price,
        current_price=current_price,
        stop_price=stop_price,
        target_price=target_price,
    )

    if status.stop_triggered:
        return "STOP_LOSS"

    if status.target_triggered:
        return "TAKE_PROFIT"

    return None


class AutomaticExitService:
    """Process saved exit plans against current paper-position prices."""

    def __init__(
        self,
        db_path: str = "data/paper_trading.db",
        *,
        commission: float = 0.0,
        slippage_pct: float = 0.001,
    ) -> None:
        self.db_path = db_path
        self.account_service = PaperAccountService(db_path)
        self.exit_plans = ExitPlanRepository(db_path)
        self.orders = PaperOrderService(
            db_path,
            commission=commission,
            slippage_pct=slippage_pct,
        )

    def process_triggered_exits(
        self,
        *,
        enabled: bool = False,
    ) -> list[AutoExitEvent]:
        """Close triggered positions when automatic exits are enabled."""

        if not enabled:
            return []

        account = self.account_service.active_account()
        positions = self.account_service.repository.list_positions(account.id)

        events: list[AutoExitEvent] = []

        for position in positions:
            plan = self.exit_plans.get_plan(
                account_id=account.id,
                ticker=position.ticker,
            )

            if plan is None:
                continue

            reason = evaluate_auto_exit_for_position(
                ticker=position.ticker,
                entry_price=position.average_entry_price,
                current_price=position.current_price,
                stop_price=plan.stop_price,
                target_price=plan.target_price,
            )

            if reason is None:
                continue

            execution = self.orders.sell_market(
                ticker=position.ticker,
                shares=position.shares,
                market_price=position.current_price,
                reason=reason,
                notes=(
                    "Automatically simulated from saved exit plan"
                ),
                confidence=5,
                atlas_score=None,
            )

            self.exit_plans.delete_plan(
                account_id=account.id,
                ticker=position.ticker,
            )

            events.append(
                AutoExitEvent(
                    ticker=position.ticker,
                    exit_reason=reason,
                    trigger_price=position.current_price,
                    filled_price=execution.filled_price,
                    shares=execution.shares,
                    realised_pnl=execution.realised_pnl,
                    order_id=execution.order_id,
                )
            )

        return events
