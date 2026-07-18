"""
dashboard.py

Reusable market analytics dashboard components for Project Atlas.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def _validate_columns(df: pd.DataFrame, required_columns: list[str]) -> bool:
    """
    Confirm that the required DataFrame columns are available.
    """

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        st.warning(
            "Dashboard data is incomplete. Missing columns: "
            + ", ".join(missing_columns)
        )
        return False

    return True


def display_market_breadth(df: pd.DataFrame) -> None:
    """
    Display BUY, HOLD and SELL market breadth.
    """

    if not _validate_columns(df, ["Signal"]):
        return

    total_stocks = len(df)

    if total_stocks == 0:
        st.info("No market data is available.")
        return

    signal_counts = (
        df["Signal"]
        .astype(str)
        .str.upper()
        .value_counts()
    )

    buy_count = int(signal_counts.get("BUY", 0))
    hold_count = int(signal_counts.get("HOLD", 0))
    sell_count = int(signal_counts.get("SELL", 0))

    buy_ratio = buy_count / total_stocks
    hold_ratio = hold_count / total_stocks
    sell_ratio = sell_count / total_stocks

    st.subheader("📊 Market Breadth")

    buy_column, hold_column, sell_column = st.columns(3)

    buy_column.metric(
        label="Bullish",
        value=buy_count,
        delta=f"{buy_ratio:.1%}",
    )

    hold_column.metric(
        label="Neutral",
        value=hold_count,
        delta=f"{hold_ratio:.1%}",
    )

    sell_column.metric(
        label="Bearish",
        value=sell_count,
        delta=f"{sell_ratio:.1%}",
        delta_color="inverse",
    )

    st.progress(
        buy_ratio,
        text=f"Bullish breadth: {buy_ratio:.1%}",
    )

    if buy_ratio >= 0.70:
        st.success("🟢 Broadly bullish market")
    elif buy_ratio >= 0.50:
        st.info("🟡 Moderately bullish market")
    elif sell_ratio >= 0.50:
        st.error("🔴 Broadly bearish market")
    else:
        st.warning("🟠 Mixed market conditions")


def display_signal_breakdown(df: pd.DataFrame) -> None:
    """
    Display an interactive doughnut chart of trading signals.
    """

    if not _validate_columns(df, ["Signal"]):
        return

    signal_data = (
        df["Signal"]
        .astype(str)
        .str.upper()
        .value_counts()
        .rename_axis("Signal")
        .reset_index(name="Stocks")
    )

    if signal_data.empty:
        st.info("No signal information is available.")
        return

    figure = px.pie(
        signal_data,
        names="Signal",
        values="Stocks",
        hole=0.55,
        title="Trading Signal Breakdown",
    )

    figure.update_traces(
        textposition="inside",
        textinfo="label+percent+value",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Stocks: %{value}<br>"
            "Share: %{percent}"
            "<extra></extra>"
        ),
    )

    figure.update_layout(
        height=420,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
        legend_title_text="Signal",
    )

    st.plotly_chart(
        figure,
        width="stretch",
    )


def display_score_distribution(df: pd.DataFrame) -> None:
    """
    Display the distribution of Atlas scores.
    """

    if not _validate_columns(df, ["Score"]):
        return

    score_data = df.copy()

    score_data["Score"] = pd.to_numeric(
        score_data["Score"],
        errors="coerce",
    )

    score_data = score_data.dropna(
        subset=["Score"]
    )

    if score_data.empty:
        st.info("No valid score information is available.")
        return

    figure = px.histogram(
        score_data,
        x="Score",
        nbins=10,
        title="Atlas Score Distribution",
        labels={
            "Score": "Atlas Score",
            "count": "Number of Stocks",
        },
    )

    figure.update_layout(
        height=420,
        bargap=0.08,
        xaxis={
            "range": [0, 100],
            "dtick": 10,
        },
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
        showlegend=False,
    )

    figure.update_traces(
        hovertemplate=(
            "Score range: %{x}<br>"
            "Stocks: %{y}"
            "<extra></extra>"
        )
    )

    st.plotly_chart(
        figure,
        width="stretch",
    )


def _prepare_ranked_table(
    df: pd.DataFrame,
    ascending: bool,
    limit: int = 10,
) -> pd.DataFrame:
    """
    Prepare a ranked stock table.
    """

    preferred_columns = [
        "Ticker",
        "Signal",
        "Score",
        "Confidence",
        "RSI",
        "Strength (%)",
        "Reasons",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in df.columns
    ]

    ranked_df = (
        df.sort_values(
            by="Score",
            ascending=ascending,
        )
        .head(limit)
        .loc[:, available_columns]
        .copy()
    )

    ranked_df.insert(
        0,
        "Rank",
        range(1, len(ranked_df) + 1),
    )

    return ranked_df


def display_top_performers(
    df: pd.DataFrame,
    limit: int = 10,
) -> None:
    """
    Display the highest-scoring stocks.
    """

    if not _validate_columns(df, ["Ticker", "Score"]):
        return

    top_stocks = _prepare_ranked_table(
        df=df,
        ascending=False,
        limit=limit,
    )

    st.subheader(f"🏆 Top {len(top_stocks)} Opportunities")

    st.dataframe(
        top_stocks,
        width="stretch",
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(
                "Rank",
                format="%d",
            ),
            "Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%d",
            ),
            "RSI": st.column_config.NumberColumn(
                "RSI",
                format="%.1f",
            ),
            "Strength (%)": st.column_config.NumberColumn(
                "Strength",
                format="%.2f%%",
            ),
        },
    )


def display_bottom_performers(
    df: pd.DataFrame,
    limit: int = 10,
) -> None:
    """
    Display the lowest-scoring stocks.
    """

    if not _validate_columns(df, ["Ticker", "Score"]):
        return

    bottom_stocks = _prepare_ranked_table(
        df=df,
        ascending=True,
        limit=limit,
    )

    st.subheader(f"⚠️ Bottom {len(bottom_stocks)} Stocks")

    st.dataframe(
        bottom_stocks,
        width="stretch",
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(
                "Rank",
                format="%d",
            ),
            "Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%d",
            ),
            "RSI": st.column_config.NumberColumn(
                "RSI",
                format="%.1f",
            ),
            "Strength (%)": st.column_config.NumberColumn(
                "Strength",
                format="%.2f%%",
            ),
        },
    )


def display_market_analytics(df: pd.DataFrame) -> None:
    """
    Display the complete Project Atlas market analytics dashboard.
    """

    st.header("📈 Market Analytics")

    display_market_breadth(df)

    st.divider()

    chart_column1, chart_column2 = st.columns(2)

    with chart_column1:
        display_signal_breakdown(df)

    with chart_column2:
        display_score_distribution(df)

    st.divider()

    leader_column, laggard_column = st.columns(2)

    with leader_column:
        display_top_performers(
            df,
            limit=10,
        )

    with laggard_column:
        display_bottom_performers(
            df,
            limit=10,
        )