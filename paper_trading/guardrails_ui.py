"""Portfolio Guardrails UI for Atlas paper trading."""

from __future__ import annotations

import streamlit as st

from .account import PaperAccountService
from .portfolio_guardrails import (
    GuardrailSettings,
    evaluate_portfolio_guardrails,
)


def display_portfolio_guardrails(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    """Display portfolio-wide trading safety status."""

    service = PaperAccountService(db_path)

    st.subheader("🚦 Portfolio Guardrails")
    st.caption(
        "Portfolio-wide rules can pause new simulated BUY entries after "
        "excessive exposure or losses."
    )

    settings_col, status_col = st.columns([1, 1.4])

    with settings_col:
        st.markdown("#### Limits")

        max_exposure = st.number_input(
            "Maximum total exposure (%)",
            min_value=10.0,
            max_value=100.0,
            value=80.0,
            step=5.0,
            key="guardrail_max_exposure",
        )

        max_positions = st.number_input(
            "Maximum open positions",
            min_value=1,
            max_value=50,
            value=8,
            step=1,
            key="guardrail_max_positions",
        )

        daily_loss = st.number_input(
            "Daily loss limit (%)",
            min_value=0.5,
            max_value=20.0,
            value=3.0,
            step=0.5,
            key="guardrail_daily_loss",
        )

        consecutive_losses = st.number_input(
            "Consecutive-loss pause",
            min_value=1,
            max_value=20,
            value=3,
            step=1,
            key="guardrail_loss_streak",
        )

    settings = GuardrailSettings(
        max_total_exposure_pct=float(max_exposure),
        max_open_positions=int(max_positions),
        daily_loss_limit_pct=float(daily_loss),
        consecutive_loss_limit=int(consecutive_losses),
    )

    status = evaluate_portfolio_guardrails(
        service,
        settings=settings,
    )

    with status_col:
        st.markdown("#### Trading Status")

        if status.trading_allowed:
            st.success("🟢 NEW PAPER BUY ENTRIES ALLOWED")
        else:
            st.error("🔴 NEW PAPER BUY ENTRIES PAUSED")

        metrics = st.columns(2)
        metrics[0].metric(
            "Portfolio Exposure",
            f"{status.exposure_pct:.1f}%",
        )
        metrics[1].metric(
            "Open Positions",
            status.open_positions,
        )

        metrics2 = st.columns(2)
        metrics2[0].metric(
            "Today's Realised P&L",
            f"${status.daily_realised_pnl:,.2f}",
        )
        metrics2[1].metric(
            "Current Loss Streak",
            status.consecutive_losses,
        )

        for blocker in status.blockers:
            st.error(blocker)

        for warning in status.warnings:
            st.warning(warning)

        if not status.blockers and not status.warnings:
            st.info("All portfolio guardrails are comfortably within limits.")

    st.caption(
        "Guardrails apply to new simulated BUY entries. SELL orders remain "
        "available so open paper positions can still be reduced or closed."
    )
