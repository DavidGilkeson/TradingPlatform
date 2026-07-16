"""
ui_components.py

Reusable Streamlit interface components for Project Atlas.
"""

import streamlit as st


def display_market_overview(df, scan_time):
    """Display the main market statistics."""

    bullish_count = int((df["Signal"] == "BUY").sum())
    bearish_count = int((df["Signal"] == "SELL").sum())
    average_score = round(float(df["Score"].mean()), 1)
    average_rsi = round(float(df["RSI"].mean()), 1)
    highest_score = int(df["Score"].max())

    metric1, metric2, metric3 = st.columns(3)
    metric4, metric5, metric6 = st.columns(3)

    metric1.metric("📈 Bullish stocks", bullish_count)
    metric2.metric("📉 Bearish stocks", bearish_count)
    metric3.metric("⭐ Average score", average_score)
    metric4.metric("📊 Average RSI", average_rsi)
    metric5.metric("🏆 Highest score", highest_score)
    metric6.metric("⚡ Scan time", f"{scan_time:.1f}s")


def display_market_pulse(df):
    """Display the percentage of bullish stocks."""

    total_stocks = len(df)
    bullish_count = int((df["Signal"] == "BUY").sum())

    bullish_ratio = (
        bullish_count / total_stocks
        if total_stocks > 0
        else 0
    )

    st.subheader("📊 Market Pulse")

    st.progress(
        bullish_ratio,
        text=f"{bullish_ratio:.1%} of analysed stocks are bullish"
    )

    if bullish_ratio >= 0.70:
        st.success("🟢 Strong bullish market")
    elif bullish_ratio >= 0.50:
        st.info("🟡 Moderately bullish market")
    elif bullish_ratio >= 0.30:
        st.warning("🟠 Weak or mixed market")
    else:
        st.error("🔴 Bearish market")


def apply_stock_filters(
    df,
    minimum_score,
    signal_filter,
    ticker_search
):
    """Apply dashboard filters to the scanner results."""

    filtered_df = df[
        df["Score"] >= minimum_score
    ].copy()

    if signal_filter != "All":
        filtered_df = filtered_df[
            filtered_df["Signal"] == signal_filter
        ]

    search_value = ticker_search.strip().upper()

    if search_value:
        filtered_df = filtered_df[
            filtered_df["Ticker"].str.contains(
                search_value,
                case=False,
                na=False
            )
        ]

    return filtered_df


def display_best_opportunity(best_stock):
    """Display the highest-ranked stock."""

    best1, best2, best3 = st.columns([1, 1, 2])

    best1.metric(
        "Ticker",
        best_stock["Ticker"]
    )

    best2.metric(
        "Score",
        f'{int(best_stock["Score"])}/100'
    )

    with best3:
        st.markdown(
            f"### {best_stock['Confidence']}"
        )

        st.write(
            best_stock["Reasons"]
        )


def display_opportunities_editor(
    filtered_df,
    watchlist
):
    """
    Display the editable favourites table.

    Returns:
        DataFrame containing the edited values.
    """

    display_columns = [
        "Ticker",
        "Close",
        "Signal",
        "Score",
        "Confidence",
        "RSI",
        "Strength (%)",
        "Reasons"
    ]

    favourite_df = filtered_df[
        display_columns
    ].head(50).copy()

    favourite_df.insert(
        0,
        "Favourite",
        favourite_df["Ticker"].isin(watchlist)
    )

    edited_df = st.data_editor(
        favourite_df,
        width="stretch",
        hide_index=True,
        disabled=[
            "Ticker",
            "Close",
            "Signal",
            "Score",
            "Confidence",
            "RSI",
            "Strength (%)",
            "Reasons"
        ],
        column_config={
            "Favourite": st.column_config.CheckboxColumn(
                "⭐",
                help="Add or remove this stock from your watchlist"
            ),
            "Close": st.column_config.NumberColumn(
                "Close",
                format="$%.2f"
            ),
            "RSI": st.column_config.NumberColumn(
                "RSI",
                format="%.2f"
            ),
            "Strength (%)": st.column_config.NumberColumn(
                "Strength",
                format="%.2f%%"
            ),
            "Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%d"
            )
        },
        key="favourites_editor"
    )

    return favourite_df, edited_df