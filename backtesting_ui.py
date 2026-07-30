"""Streamlit integration for Atlas strategies and the universal backtester."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from backtesting import (
    BacktestConfig,
    backtest_strategy,
    compare_strategies,
)
from backtesting.visualisations import (
    display_backtest_result,
    display_strategy_comparison,
)
from strategies import get_strategy, load_strategies, strategy_options


def display_backtesting_lab(
    ticker: str,
    market_data: pd.DataFrame,
) -> None:
    """Display the complete Atlas single-asset backtesting lab."""

    st.header("🧪 Atlas Backtesting Lab")
    st.caption(
        "Test any registered strategy using consistent execution, cost, "
        "portfolio, and performance assumptions."
    )

    settings1, settings2, settings3, settings4 = st.columns(4)

    with settings1:
        initial_capital = st.number_input(
            "Starting Capital",
            min_value=100.0,
            value=10_000.0,
            step=1_000.0,
        )

    with settings2:
        position_size_pct = st.slider(
            "Position Size",
            min_value=10,
            max_value=100,
            value=100,
            step=5,
        ) / 100

    with settings3:
        commission = st.number_input(
            "Commission Per Order",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

    with settings4:
        slippage_pct = st.number_input(
            "Slippage (%)",
            min_value=0.0,
            value=0.10,
            step=0.05,
        ) / 100

    config = BacktestConfig(
        ticker=ticker,
        initial_capital=initial_capital,
        position_size_pct=position_size_pct,
        commission=commission,
        slippage_pct=slippage_pct,
    )

    single_tab, comparison_tab = st.tabs(
        ["Single Strategy", "Compare Strategies"]
    )

    with single_tab:
        options = strategy_options()
        selected_key = st.selectbox(
            "Strategy",
            options=list(options),
            format_func=lambda key: options[key],
            key=f"backtest_strategy_{ticker}",
        )

        strategy = get_strategy(selected_key)

        if st.button(
            "Run Backtest",
            type="primary",
            width="stretch",
        ):
            with st.spinner("Running Atlas backtest..."):
                result = backtest_strategy(
                    strategy,
                    market_data,
                    config=config,
                )
            st.session_state["atlas_backtest_result"] = result

        result = st.session_state.get("atlas_backtest_result")
        if result is not None:
            display_backtest_result(result)

    with comparison_tab:
        st.write(
            "Run every registered strategy against the same ticker and "
            "assumptions."
        )

        if st.button(
            "Compare All Strategies",
            width="stretch",
        ):
            with st.spinner("Comparing Atlas strategies..."):
                comparison, results = compare_strategies(
                    load_strategies(),
                    market_data,
                    config=config,
                )

            st.session_state["atlas_strategy_comparison"] = comparison
            st.session_state["atlas_strategy_results"] = results

        comparison = st.session_state.get("atlas_strategy_comparison")

        if comparison is not None:
            display_strategy_comparison(comparison)
