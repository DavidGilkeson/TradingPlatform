"""Risk Manager UI for Atlas paper trading."""

from __future__ import annotations
import streamlit as st

from .account import PaperAccountService
from .risk_manager import calculate_position_size, validate_order_risk


def display_risk_manager(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    """Display position sizing and pre-trade risk planning."""

    service = PaperAccountService(db_path)
    account = service.active_account()
    snapshot = service.snapshot(persist=False)

    st.subheader("🛡️ Atlas Risk Manager")
    st.caption(
        "Plan simulated trades by defining the maximum account risk "
        "before choosing position size."
    )

    settings, planner = st.columns([1, 1.5])

    with settings:
        st.markdown("#### Risk Rules")
        risk_pct = st.number_input(
            "Maximum risk per trade (%)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            key="risk_manager_risk_pct",
        )
        max_position_pct = st.number_input(
            "Maximum position size (%)",
            min_value=1.0,
            max_value=100.0,
            value=20.0,
            step=1.0,
            key="risk_manager_max_position",
        )
        minimum_rr = st.number_input(
            "Minimum reward/risk",
            min_value=0.5,
            max_value=10.0,
            value=2.0,
            step=0.25,
            key="risk_manager_min_rr",
        )

    with planner:
        st.markdown("#### Trade Planner")
        entry = st.number_input(
            "Entry price",
            min_value=0.01,
            value=100.0,
            step=0.50,
            key="risk_manager_entry",
        )
        stop = st.number_input(
            "Stop-loss price",
            min_value=0.01,
            value=95.0,
            step=0.50,
            key="risk_manager_stop",
        )
        target = st.number_input(
            "Take-profit target",
            min_value=0.01,
            value=110.0,
            step=0.50,
            key="risk_manager_target",
        )

    try:
        plan = calculate_position_size(
            account_equity=float(snapshot.equity),
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            risk_pct=risk_pct,
            max_position_pct=max_position_pct,
        )
    except ValueError as error:
        st.error(str(error))
        return

    st.divider()

    metrics = st.columns(6)
    metrics[0].metric("Account Equity", f"${plan.account_equity:,.2f}")
    metrics[1].metric("Max $ Risk", f"${plan.max_risk_amount:,.2f}")
    metrics[2].metric("Risk / Share", f"${plan.risk_per_share:,.2f}")
    metrics[3].metric("Suggested Shares", f"{plan.recommended_shares:,}")
    metrics[4].metric("Position Value", f"${plan.position_value:,.2f}")
    metrics[5].metric(
        "Reward / Risk",
        "—" if plan.reward_risk_ratio is None
        else f"{plan.reward_risk_ratio:.2f}:1",
    )

    decision = validate_order_risk(
        account_equity=float(snapshot.equity),
        cash=float(account.cash),
        shares=plan.recommended_shares,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        risk_pct_limit=risk_pct,
        max_position_pct=max_position_pct,
        minimum_reward_risk=minimum_rr,
    )

    if plan.recommended_shares == 0:
        st.warning(
            "The current risk limits do not allow even one share "
            "at this stop distance."
        )
    elif decision.allowed:
        st.success("Risk check passed for the suggested simulated position.")
    else:
        for blocker in decision.blockers:
            st.error(blocker)

    for warning in decision.warnings:
        st.warning(warning)

    st.info(
        "Risk Manager is for paper-trading discipline and simulation. "
        "It does not provide financial advice or guarantee outcomes."
    )
