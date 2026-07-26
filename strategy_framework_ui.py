"""Reusable Streamlit UI for the Atlas strategy framework."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from strategies import get_strategy, strategy_options


def display_strategy_framework(
    ticker: str,
    selected_data: pd.DataFrame,
) -> None:
    """Run a selected modular strategy and display its latest results."""

    st.subheader("🧪 Atlas Strategy Framework")
    st.caption(
        "Run any registered strategy through one consistent interface."
    )

    options = strategy_options()
    selected_key = st.selectbox(
        "Strategy",
        options=list(options),
        format_func=lambda key: options[key],
        key=f"framework_strategy_{ticker}",
    )

    strategy = get_strategy(selected_key)

    st.write(strategy.description)

    try:
        result = strategy.run(selected_data)
    except (TypeError, ValueError) as error:
        st.error(f"Strategy could not run: {error}")
        return

    summary = result.summary()
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Rows Analysed", summary["rows"])
    metric2.metric("Buy Signals", summary["buy_count"])
    metric3.metric("Sell Signals", summary["sell_count"])
    metric4.metric("Hold Rows", summary["hold_count"])

    latest = result.signals.tail(100).copy()

    chart_columns = [
        column
        for column in ["Close", "Fast MA", "Slow MA", "MA20", "MA50"]
        if column in latest.columns
    ]

    if chart_columns:
        st.line_chart(latest[chart_columns])

    visible_columns = [
        column
        for column in [
            "Close",
            "Signal",
            "RSI",
            "Momentum Return",
            "Relative Volume",
            "Strategy Score",
        ]
        if column in latest.columns
    ]

    st.dataframe(
        latest[visible_columns].tail(30),
        width="stretch",
    )

    latest_signal = str(result.signals["Signal"].iloc[-1])
    st.info(f"Latest {ticker} signal: **{latest_signal}**")
