"""Stop-loss and take-profit tracking UI."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .account import PaperAccountService
from .exit_plans import (
    ExitPlanRepository,
    evaluate_exit_plan,
    validate_exit_plan,
)


def display_exit_plan_manager(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    """Display stop/target plans for open paper positions."""

    service = PaperAccountService(db_path)
    account = service.active_account()
    positions = service.repository.list_positions(account.id)
    plans = ExitPlanRepository(db_path)

    st.subheader("🎯 Stop-Loss & Take-Profit Plans")
    st.caption(
        "Track planned exit levels for open simulated positions. "
        "Sprint 30.5 monitors these levels but does not auto-close trades."
    )

    if not positions:
        st.info("No open paper positions.")
        return

    ticker = st.selectbox(
        "Position",
        options=[position.ticker for position in positions],
        key="exit_plan_ticker",
    )

    position = next(
        p for p in positions if p.ticker == ticker
    )

    existing = plans.get_plan(
        account_id=account.id,
        ticker=ticker,
    )

    default_stop = (
        existing.stop_price
        if existing and existing.stop_price is not None
        else position.average_entry_price * 0.95
    )

    default_target = (
        existing.target_price
        if existing and existing.target_price is not None
        else position.average_entry_price * 1.10
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric(
        "Average Entry",
        f"${position.average_entry_price:,.2f}",
    )
    metric2.metric(
        "Current Price",
        f"${position.current_price:,.2f}",
    )
    metric3.metric(
        "Unrealised P&L",
        f"${position.unrealised_pnl:,.2f}",
    )

    col1, col2 = st.columns(2)

    with col1:
        stop_price = st.number_input(
            "Stop-loss price",
            min_value=0.01,
            value=float(default_stop),
            step=0.01,
            format="%.2f",
            key=f"exit_stop_{ticker}",
        )

    with col2:
        target_price = st.number_input(
            "Take-profit target",
            min_value=0.01,
            value=float(default_target),
            step=0.01,
            format="%.2f",
            key=f"exit_target_{ticker}",
        )

    try:
        validate_exit_plan(
            entry_price=position.average_entry_price,
            stop_price=stop_price,
            target_price=target_price,
        )

        status = evaluate_exit_plan(
            ticker=ticker,
            entry_price=position.average_entry_price,
            current_price=position.current_price,
            stop_price=stop_price,
            target_price=target_price,
        )

    except ValueError as error:
        st.error(str(error))
        return

    metrics = st.columns(4)

    metrics[0].metric(
        "Distance to Stop",
        (
            "—"
            if status.distance_to_stop_pct is None
            else f"{status.distance_to_stop_pct:.2%}"
        ),
    )
    metrics[1].metric(
        "Distance to Target",
        (
            "—"
            if status.distance_to_target_pct is None
            else f"{status.distance_to_target_pct:.2%}"
        ),
    )
    metrics[2].metric(
        "Reward / Risk",
        (
            "—"
            if status.reward_risk_ratio is None
            else f"{status.reward_risk_ratio:.2f}:1"
        ),
    )
    metrics[3].metric(
        "Plan Status",
        (
            "STOP HIT"
            if status.stop_triggered
            else "TARGET HIT"
            if status.target_triggered
            else "ACTIVE"
        ),
    )

    if status.stop_triggered:
        st.error(
            "Current price is at or below the planned stop. "
            "Review the simulated position."
        )
    elif status.target_triggered:
        st.success(
            "Current price is at or above the planned target. "
            "Review the simulated position."
        )
    else:
        st.info("Price remains between the planned stop and target.")

    save_col, delete_col = st.columns(2)

    with save_col:
        if st.button(
            "Save Exit Plan",
            type="primary",
            width="stretch",
            key="save_exit_plan",
        ):
            plans.save_plan(
                account_id=account.id,
                ticker=ticker,
                stop_price=stop_price,
                target_price=target_price,
            )
            st.success("Exit plan saved.")
            st.rerun()

    with delete_col:
        if st.button(
            "Clear Exit Plan",
            width="stretch",
            key="clear_exit_plan",
        ):
            plans.delete_plan(
                account_id=account.id,
                ticker=ticker,
            )
            st.success("Exit plan cleared.")
            st.rerun()

    st.divider()
    st.markdown("#### All Open Position Plans")

    rows = []

    for open_position in positions:
        plan = plans.get_plan(
            account_id=account.id,
            ticker=open_position.ticker,
        )

        if plan is None:
            rows.append(
                {
                    "Ticker": open_position.ticker,
                    "Current": open_position.current_price,
                    "Stop": None,
                    "Target": None,
                    "Status": "No plan",
                }
            )
            continue

        try:
            plan_status = evaluate_exit_plan(
                ticker=open_position.ticker,
                entry_price=open_position.average_entry_price,
                current_price=open_position.current_price,
                stop_price=plan.stop_price,
                target_price=plan.target_price,
            )
        except ValueError:
            status_text = "Invalid plan"
        else:
            status_text = (
                "Stop hit"
                if plan_status.stop_triggered
                else "Target hit"
                if plan_status.target_triggered
                else "Active"
            )

        rows.append(
            {
                "Ticker": open_position.ticker,
                "Current": open_position.current_price,
                "Stop": plan.stop_price,
                "Target": plan.target_price,
                "Status": status_text,
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
    )
