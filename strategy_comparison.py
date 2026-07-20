"""
strategy_comparison.py

Compare multiple moving-average strategies for Project Atlas.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from backtester import run_backtest


DEFAULT_STRATEGIES = {
    "Fast Momentum — 5/20": {
        "short_window": 5,
        "long_window": 20,
    },
    "Swing Trend — 10/30": {
        "short_window": 10,
        "long_window": 30,
    },
    "Classic Crossover — 20/50": {
        "short_window": 20,
        "long_window": 50,
    },
    "Medium Trend — 50/100": {
        "short_window": 50,
        "long_window": 100,
    },
    "Golden Cross — 50/200": {
        "short_window": 50,
        "long_window": 200,
    },
}


def _prepare_price_series(
    prices: pd.Series,
) -> pd.Series:
    """
    Convert price data into a clean numeric Series.
    """

    clean_prices = pd.to_numeric(
        prices,
        errors="coerce",
    ).dropna()

    clean_prices = clean_prices.sort_index()

    return clean_prices


def compare_strategies(
    open_prices: pd.Series,
    close_prices: pd.Series,
    starting_balance: float,
    strategies: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Run several moving-average strategies against one stock.

    Returns:
        results_df:
            Summary results for every valid strategy.

        detailed_results:
            Complete backtest output for each strategy.
    """

    strategies = strategies or DEFAULT_STRATEGIES

    clean_open = _prepare_price_series(
        open_prices
    )

    clean_close = _prepare_price_series(
        close_prices
    )

    common_index = clean_open.index.intersection(
        clean_close.index
    )

    clean_open = clean_open.loc[common_index]
    clean_close = clean_close.loc[common_index]

    summary_rows = []
    detailed_results = {}

    for strategy_name, settings in strategies.items():
        short_window = int(
            settings["short_window"]
        )

        long_window = int(
            settings["long_window"]
        )

        if short_window >= long_window:
            continue

        if len(clean_close) < long_window:
            continue

        ma_short = clean_close.rolling(
            window=short_window
        ).mean()

        ma_long = clean_close.rolling(
            window=long_window
        ).mean()

        try:
            result = run_backtest(
                open_prices=clean_open,
                close_prices=clean_close,
                ma_short=ma_short,
                ma_long=ma_long,
                starting_balance=starting_balance,
            )

        except Exception:
            continue

        detailed_results[strategy_name] = result

        summary_rows.append(
            {
                "Strategy": strategy_name,
                "Short MA": short_window,
                "Long MA": long_window,
                "Ending Balance": float(
                    result.get(
                        "Ending Balance",
                        starting_balance,
                    )
                ),
                "Strategy Return (%)": float(
                    result.get(
                        "Strategy Return (%)",
                        0,
                    )
                ),
                "Buy and Hold Return (%)": float(
                    result.get(
                        "Buy and Hold Return (%)",
                        0,
                    )
                ),
                "Outperformance (%)": float(
                    result.get(
                        "Outperformance (%)",
                        0,
                    )
                ),
                "Win Rate (%)": float(
                    result.get(
                        "Win Rate (%)",
                        0,
                    )
                ),
                "Maximum Drawdown (%)": float(
                    result.get(
                        "Maximum Drawdown (%)",
                        0,
                    )
                ),
                "Number of Trades": int(
                    result.get(
                        "Number of Trades",
                        0,
                    )
                ),
            }
        )

    if not summary_rows:
        return pd.DataFrame(), {}

    results_df = pd.DataFrame(
        summary_rows
    )

    results_df = results_df.sort_values(
        by=[
            "Strategy Return (%)",
            "Maximum Drawdown (%)",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(
        drop=True
    )

    results_df.insert(
        0,
        "Rank",
        range(
            1,
            len(results_df) + 1,
        ),
    )

    return results_df, detailed_results


def display_strategy_metrics(
    results_df: pd.DataFrame,
) -> None:
    """
    Display headline statistics for the winning strategy.
    """

    if results_df.empty:
        return

    winner = results_df.iloc[0]

    metric1, metric2, metric3 = st.columns(3)
    metric4, metric5, metric6 = st.columns(3)

    metric1.metric(
        label="Best Strategy",
        value=winner["Strategy"],
    )

    metric2.metric(
        label="Strategy Return",
        value=(
            f'{winner["Strategy Return (%)"]:.2f}%'
        ),
    )

    metric3.metric(
        label="Outperformance",
        value=(
            f'{winner["Outperformance (%)"]:.2f}%'
        ),
    )

    metric4.metric(
        label="Win Rate",
        value=(
            f'{winner["Win Rate (%)"]:.1f}%'
        ),
    )

    metric5.metric(
        label="Maximum Drawdown",
        value=(
            f'{winner["Maximum Drawdown (%)"]:.1f}%'
        ),
    )

    metric6.metric(
        label="Completed Trades",
        value=int(
            winner["Number of Trades"]
        ),
    )


def display_strategy_table(
    results_df: pd.DataFrame,
) -> None:
    """
    Display ranked strategy results.
    """

    st.subheader("🏆 Strategy Rankings")

    st.dataframe(
        results_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(
                format="%d",
            ),
            "Short MA": st.column_config.NumberColumn(
                format="%d",
            ),
            "Long MA": st.column_config.NumberColumn(
                format="%d",
            ),
            "Ending Balance": (
                st.column_config.NumberColumn(
                    format="$%.2f",
                )
            ),
            "Strategy Return (%)": (
                st.column_config.NumberColumn(
                    format="%.2f%%",
                )
            ),
            "Buy and Hold Return (%)": (
                st.column_config.NumberColumn(
                    format="%.2f%%",
                )
            ),
            "Outperformance (%)": (
                st.column_config.NumberColumn(
                    format="%.2f%%",
                )
            ),
            "Win Rate (%)": (
                st.column_config.NumberColumn(
                    format="%.1f%%",
                )
            ),
            "Maximum Drawdown (%)": (
                st.column_config.NumberColumn(
                    format="%.1f%%",
                )
            ),
            "Number of Trades": (
                st.column_config.NumberColumn(
                    format="%d",
                )
            ),
        },
    )


def display_strategy_chart(
    results_df: pd.DataFrame,
) -> None:
    """
    Display strategy returns in an interactive chart.
    """

    chart_df = results_df.sort_values(
        by="Strategy Return (%)",
        ascending=True,
    )

    figure = px.bar(
        chart_df,
        x="Strategy Return (%)",
        y="Strategy",
        orientation="h",
        title="Strategy Return Comparison",
        text_auto=".2f",
        hover_data={
            "Outperformance (%)": ":.2f",
            "Win Rate (%)": ":.1f",
            "Maximum Drawdown (%)": ":.1f",
            "Number of Trades": True,
        },
    )

    figure.update_layout(
        height=430,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
        xaxis_title="Return (%)",
        yaxis_title=None,
    )

    st.plotly_chart(
        figure,
        width="stretch",
    )


def display_equity_curve_comparison(
    detailed_results: dict,
) -> None:
    """
    Compare portfolio equity curves from each strategy.
    """

    equity_data = {}

    for strategy_name, result in detailed_results.items():
        equity_curve = result.get(
            "Equity Curve"
        )

        if equity_curve is None:
            continue

        if isinstance(
            equity_curve,
            pd.DataFrame,
        ):
            if equity_curve.empty:
                continue

            equity_series = equity_curve.iloc[
                :,
                0,
            ]

        elif isinstance(
            equity_curve,
            pd.Series,
        ):
            equity_series = equity_curve

        else:
            continue

        equity_data[strategy_name] = (
            pd.to_numeric(
                equity_series,
                errors="coerce",
            )
        )

    if not equity_data:
        return

    equity_df = pd.DataFrame(
        equity_data
    )

    st.subheader("📈 Equity Curve Comparison")

    st.line_chart(
        equity_df,
        width="stretch",
    )


def display_custom_strategy_controls() -> dict:
    """
    Let the user add one custom MA strategy.
    """

    st.subheader("⚙️ Custom Strategy")

    custom_column1, custom_column2 = st.columns(2)

    short_window = custom_column1.number_input(
        label="Short moving average",
        min_value=2,
        max_value=199,
        value=15,
        step=1,
        key="comparison_short_window",
    )

    long_window = custom_column2.number_input(
        label="Long moving average",
        min_value=3,
        max_value=400,
        value=60,
        step=1,
        key="comparison_long_window",
    )

    strategies = DEFAULT_STRATEGIES.copy()

    if short_window < long_window:
        custom_name = (
            f"Custom Strategy — "
            f"{short_window}/{long_window}"
        )

        strategies[custom_name] = {
            "short_window": short_window,
            "long_window": long_window,
        }

    else:
        st.warning(
            "The short moving average must be lower "
            "than the long moving average."
        )

    return strategies


def display_strategy_comparison(
    ticker: str,
    selected_data: dict,
) -> None:
    """
    Display the complete Project Atlas strategy comparison lab.
    """

    st.header("🧪 Strategy Comparison Lab")

    st.caption(
        f"Compare multiple moving-average strategies "
        f"against {ticker} using the same price history."
    )

    required_fields = [
        "open",
        "close",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in selected_data
    ]

    if missing_fields:
        st.warning(
            "Strategy comparison data is incomplete. Missing: "
            + ", ".join(missing_fields)
        )
        return

    starting_balance = st.number_input(
        label="Starting balance",
        min_value=1000,
        max_value=1_000_000,
        value=10_000,
        step=1000,
        key=f"comparison_balance_{ticker}",
    )

    strategies = display_custom_strategy_controls()

    if st.button(
        label="🚀 Compare Strategies",
        type="primary",
        width="stretch",
        key=f"compare_strategies_{ticker}",
    ):
        with st.spinner(
            f"Testing strategies on {ticker}...",
            show_time=True,
        ):
            results_df, detailed_results = (
                compare_strategies(
                    open_prices=selected_data["open"],
                    close_prices=selected_data["close"],
                    starting_balance=starting_balance,
                    strategies=strategies,
                )
            )

        if results_df.empty:
            st.warning(
                "No strategies could be tested. "
                "The selected stock may not have enough "
                "historical price data."
            )
            return

        st.session_state[
            f"strategy_results_{ticker}"
        ] = results_df

        st.session_state[
            f"strategy_details_{ticker}"
        ] = detailed_results

    results_df = st.session_state.get(
        f"strategy_results_{ticker}"
    )

    detailed_results = st.session_state.get(
        f"strategy_details_{ticker}"
    )

    if results_df is None or results_df.empty:
        return

    st.success(
        f"{len(results_df)} strategies compared "
        f"successfully for {ticker}."
    )

    display_strategy_metrics(
        results_df
    )

    st.divider()

    chart_column, table_column = st.columns(
        [1, 1.35]
    )

    with chart_column:
        display_strategy_chart(
            results_df
        )

    with table_column:
        display_strategy_table(
            results_df
        )

    if detailed_results:
        st.divider()

        display_equity_curve_comparison(
            detailed_results
        )

    st.divider()

    csv_data = results_df.to_csv(
        index=False
    )

    st.download_button(
        label="📥 Download Strategy Results",
        data=csv_data,
        file_name=(
            f"{ticker.lower()}_strategy_comparison.csv"
        ),
        mime="text/csv",
        width="stretch",
        key=f"download_strategy_results_{ticker}",
    )