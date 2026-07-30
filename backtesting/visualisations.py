"""Reusable Streamlit components for Atlas backtest results."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from .equity_curve import calculate_drawdown
from .models import BacktestResult


def _currency(value: float | int | None) -> str:
    if value is None or not math.isfinite(float(value)):
        return "—"
    return f"${float(value):,.2f}"


def _percent(value: float | int | None) -> str:
    if value is None or not math.isfinite(float(value)):
        return "—"
    return f"{float(value):.2%}"


def _number(value: float | int | None, digits: int = 2) -> str:
    if value is None or not math.isfinite(float(value)):
        return "—"
    return f"{float(value):.{digits}f}"


def display_backtest_result(result: BacktestResult) -> None:
    """Display metrics, curves, and completed trades in Streamlit."""

    st.subheader(
        f"📈 {result.strategy_name} Backtest — {result.ticker}"
    )

    metrics = result.metrics

    first_row = st.columns(5)
    first_row[0].metric("Final Equity", _currency(metrics["final_equity"]))
    first_row[1].metric("Total Return", _percent(metrics["total_return"]))
    first_row[2].metric("CAGR", _percent(metrics["cagr"]))
    first_row[3].metric("Sharpe", _number(metrics["sharpe_ratio"]))
    first_row[4].metric("Max Drawdown", _percent(metrics["max_drawdown"]))

    second_row = st.columns(5)
    second_row[0].metric("Trades", int(metrics["total_trades"]))
    second_row[1].metric("Win Rate", _percent(metrics["win_rate"]))
    second_row[2].metric(
        "Profit Factor",
        _number(metrics["profit_factor"]),
    )
    second_row[3].metric(
        "Exposure",
        _percent(metrics["exposure"]),
    )
    second_row[4].metric(
        "Average Trade",
        _currency(metrics["average_trade"]),
    )

    st.markdown("#### Equity Curve")
    st.line_chart(result.equity_curve[["Equity"]])

    drawdown = calculate_drawdown(result.equity_curve["Equity"])
    st.markdown("#### Drawdown")
    st.area_chart(drawdown[["Drawdown Pct"]])

    trades = result.trades_frame()

    st.markdown("#### Trade Explorer")
    if trades.empty:
        st.info("This strategy did not complete any trades.")
    else:
        display = trades.copy()
        display["return_pct"] = display["return_pct"].map(
            lambda value: f"{value:.2%}"
        )
        display["pnl"] = display["pnl"].map(
            lambda value: f"${value:,.2f}"
        )
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
        )

    with st.expander("Full Performance Metrics"):
        metrics_frame = pd.DataFrame(
            {
                "Metric": list(metrics.keys()),
                "Value": list(metrics.values()),
            }
        )
        st.dataframe(metrics_frame, width="stretch", hide_index=True)

    st.caption(
        "Backtests are hypothetical and depend on historical data, signal "
        "quality, execution assumptions, and costs. They are not guarantees "
        "of future performance."
    )


def display_strategy_comparison(comparison: pd.DataFrame) -> None:
    """Display a strategy leaderboard."""

    st.subheader("🏆 Strategy Leaderboard")

    if comparison.empty:
        st.info("No strategy comparison results are available.")
        return

    display = comparison.copy()

    for column in ["Total Return", "CAGR", "Max Drawdown", "Win Rate"]:
        if column in display.columns:
            display[column] = display[column].map(
                lambda value: "—" if pd.isna(value) else f"{value:.2%}"
            )

    for column in ["Sharpe Ratio", "Sortino Ratio", "Profit Factor"]:
        if column in display.columns:
            display[column] = display[column].map(
                lambda value: "—" if pd.isna(value) else f"{value:.2f}"
            )

    if "Final Equity" in display.columns:
        display["Final Equity"] = display["Final Equity"].map(
            lambda value: f"${value:,.2f}"
        )

    st.dataframe(display, width="stretch")
