"""
app.py

Streamlit dashboard for Project Atlas.
"""

import time

import streamlit as st

from config import SP500_URL, TICKER_FILE
from scanner import scan_stocks
from utils import download_sp500_tickers


# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Project Atlas",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Project Atlas")
st.caption(
    "S&P 500 market scanner using moving averages, RSI, "
    "volume analysis and stock scoring."
)


# --------------------------------------------------
# Sidebar controls
# --------------------------------------------------
with st.sidebar:
    st.header("Scanner Controls")

    minimum_score = st.slider(
        "Minimum score",
        min_value=0,
        max_value=100,
        value=70,
        step=5
    )

    signal_filter = st.selectbox(
        "Trading signal",
        options=["All", "BUY", "SELL", "HOLD"]
    )

    ticker_search = st.text_input(
        "Search ticker",
        placeholder="Example: AAPL"
    )

    run_scanner = st.button(
        "🚀 Scan Market",
        type="primary",
        width="stretch"
    )


# --------------------------------------------------
# Run scanner
# --------------------------------------------------
if run_scanner:
    scan_start = time.perf_counter()

    with st.spinner("Loading S&P 500 ticker symbols..."):
        stocks = download_sp500_tickers(
            SP500_URL,
            TICKER_FILE
        )

    if not stocks:
        st.error("No ticker symbols could be loaded.")
        st.stop()

    with st.spinner(
        f"Scanning {len(stocks)} stocks. This may take a few minutes..."
    ):
        df, chart_data = scan_stocks(stocks)

    scan_time = time.perf_counter() - scan_start

    if df.empty:
        st.error("The scanner did not generate any results.")
        st.stop()

    # Save results so they remain available during Streamlit reruns
    st.session_state["scan_results"] = df
    st.session_state["chart_data"] = chart_data
    st.session_state["scan_time"] = scan_time

    st.success(
        f"Market scan complete — {len(df)} stocks analysed."
    )


# --------------------------------------------------
# Display saved results
# --------------------------------------------------
if "scan_results" in st.session_state:
    df = st.session_state["scan_results"]
    chart_data = st.session_state["chart_data"]
    scan_time = st.session_state["scan_time"]

    # Market summary metrics
    bullish_count = int((df["Signal"] == "BUY").sum())
    bearish_count = int((df["Signal"] == "SELL").sum())
    average_score = round(float(df["Score"].mean()), 1)

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        label="📈 Bullish stocks",
        value=bullish_count
    )

    metric2.metric(
        label="📉 Bearish stocks",
        value=bearish_count
    )

    metric3.metric(
        label="⭐ Average score",
        value=average_score
    )

    metric4.metric(
        label="⚡ Scan time",
        value=f"{scan_time:.1f}s"
    )

    st.divider()

    # --------------------------------------------------
    # Apply filters
    # --------------------------------------------------
    filtered_df = df[df["Score"] >= minimum_score].copy()

    if signal_filter != "All":
        filtered_df = filtered_df[
            filtered_df["Signal"] == signal_filter
        ]

    if ticker_search.strip():
        search_value = ticker_search.strip().upper()

        filtered_df = filtered_df[
            filtered_df["Ticker"].str.contains(
                search_value,
                case=False,
                na=False
            )
        ]

    # --------------------------------------------------
    # Best opportunity card
    # --------------------------------------------------
    st.subheader("🏆 Best Opportunity")

    if filtered_df.empty:
        st.warning(
            "No stocks match the current filters. "
            "Try lowering the minimum score."
        )

    else:
        best_stock = filtered_df.iloc[0]

        best1, best2, best3 = st.columns([1, 1, 2])

        best1.metric(
            label="Ticker",
            value=best_stock["Ticker"]
        )

        best2.metric(
            label="Score",
            value=f'{int(best_stock["Score"])}/100'
        )

        with best3:
            st.markdown(
                f"### {best_stock['Confidence']}"
            )
            st.write(best_stock["Reasons"])

        st.divider()

        # --------------------------------------------------
        # Results table
        # --------------------------------------------------
        st.subheader(
            f"🔥 Opportunities ({len(filtered_df)} matches)"
        )

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

        display_df = filtered_df[
            display_columns
        ].head(50)

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
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
            }
        )

        # --------------------------------------------------
        # CSV download
        # --------------------------------------------------
        csv_data = filtered_df.to_csv(index=False)

        st.download_button(
            label="📥 Download Filtered Results",
            data=csv_data,
            file_name="project_atlas_results.csv",
            mime="text/csv"
        )

else:
    st.info(
        "Use the sidebar and press **Scan Market** to begin."
    )