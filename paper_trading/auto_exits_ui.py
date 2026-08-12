"""Automatic Exit Controls UI for Atlas paper trading."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .account import PaperAccountService
from .auto_exits import AutomaticExitService
from .exit_plans import ExitPlanRepository, evaluate_exit_plan


def display_automatic_exit_controls(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    """Display monitoring and optional automatic simulated exits."""

    st.subheader("🤖 Automatic Paper Exits")
    st.caption(
        "Optionally simulate closing a paper position when its saved "
        "stop-loss or take-profit level is reached."
    )

    enabled = st.toggle(
        "Enable automatic simulated exits",
        value=False,
        key="auto_exit_enabled",
    )

    st.warning(
        "This affects paper positions only. No live brokerage orders are sent."
    )

    account_service = PaperAccountService(db_path)
    account = account_service.active_account()
    positions = account_service.repository.list_positions(account.id)
    plans = ExitPlanRepository(db_path)

    rows = []

    for position in positions:
        plan = plans.get_plan(
            account_id=account.id,
            ticker=position.ticker,
        )

        if plan is None:
            rows.append(
                {
                    "Ticker": position.ticker,
                    "Current": position.current_price,
                    "Stop": None,
                    "Target": None,
                    "Trigger": "No plan",
                }
            )
            continue

        try:
            status = evaluate_exit_plan(
                ticker=position.ticker,
                entry_price=position.average_entry_price,
                current_price=position.current_price,
                stop_price=plan.stop_price,
                target_price=plan.target_price,
            )
        except ValueError:
            trigger = "Invalid plan"
        else:
            trigger = (
                "STOP LOSS"
                if status.stop_triggered
                else "TAKE PROFIT"
                if status.target_triggered
                else "Waiting"
            )

        rows.append(
            {
                "Ticker": position.ticker,
                "Current": position.current_price,
                "Stop": plan.stop_price,
                "Target": plan.target_price,
                "Trigger": trigger,
            }
        )

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No open paper positions.")

    if st.button(
        "Check Exit Triggers Now",
        type="primary",
        width="stretch",
        key="process_auto_exits",
    ):
        service = AutomaticExitService(db_path)

        events = service.process_triggered_exits(
            enabled=enabled,
        )

        if not enabled:
            st.info(
                "Automatic exits are disabled. Atlas checked the plans "
                "but did not close any simulated positions."
            )
        elif not events:
            st.info("No saved stop-loss or take-profit levels were triggered.")
        else:
            for event in events:
                if event.exit_reason == "STOP_LOSS":
                    st.error(
                        f"{event.ticker} paper position closed by STOP LOSS "
                        f"@ ${event.filled_price:,.2f} · "
                        f"P&L ${event.realised_pnl:,.2f}"
                    )
                else:
                    st.success(
                        f"{event.ticker} paper position closed by TAKE PROFIT "
                        f"@ ${event.filled_price:,.2f} · "
                        f"P&L ${event.realised_pnl:,.2f}"
                    )

            st.rerun()

    st.caption(
        "For repeatable testing, trigger checks run only when you press "
        "'Check Exit Triggers Now'. A future sprint can schedule these checks."
    )
