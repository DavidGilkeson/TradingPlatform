import time

import streamlit as st

from config import SP500_URL, TICKER_FILE
from scanner import scan_stocks
from utils import download_sp500_tickers

st.set_page_config(
    page_title="Project Atlas",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Project Atlas")
st.subheader("AI Stock Scanner")

# Run button
if st.button("🚀 Scan Market"):

    start = time.perf_counter()

    # Download ticker list
    with st.spinner("Downloading S&P 500..."):
        stocks = download_sp500_tickers(
            SP500_URL,
            TICKER_FILE
        )

    # Scan stocks
    with st.spinner("Scanning market..."):
        df, chart_data = scan_stocks(stocks)

    finish = time.perf_counter()

    # Success message
    st.success("Market Scan Complete!")

    # -------------------------
    # Dashboard Metrics
    # -------------------------

    bullish = len(df[df["Signal"] == "BUY"])
    bearish = len(df[df["Signal"] == "SELL"])
    average_score = round(df["Score"].mean(), 1)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("📈 Bullish", bullish)
    col2.metric("📉 Bearish", bearish)
    col3.metric("⭐ Avg Score", average_score)
    col4.metric("⚡ Scan Time", f"{finish-start:.1f}s")

    st.divider()

    st.subheader("🔥 Top 20 Opportunities")

    st.dataframe(
        df.head(20),
        width="stretch"
    )

    st.download_button(
        "📥 Download Results",
        df.to_csv(index=False),
        file_name="stock_signals.csv",
        mime="text/csv"
    )