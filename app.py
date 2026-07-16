"""
app.py

Streamlit dashboard for Project Atlas.

Features:
- S&P 500 market scanner
- Market Pulse
- Score and signal filters
- Ticker search
- Best opportunity summary
- Persistent watchlist
- Interactive Plotly charts
- Strategy backtesting
- Editable favourites table
- CSV download
"""

import time

import streamlit as st

from backtester import run_backtest
from charts import create_stock_chart
from config import SP500_URL, TICKER_FILE
from scanner import scan_stocks
from ui_components import (
    apply_stock_filters,
    display_best_opportunity,
    display_market_overview,
    display_market_pulse,
    display_opportunities_editor,
)
from utils import download_sp500_tickers
from watchlist import (
    add_stock,
    load_watchlist,
    remove_stock,
    replace_watchlist,
)


# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Project Atlas",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Project Atlas")

st.caption(
    "S&P 500 market scanner using moving averages, RSI, "
    "volume analysis, stock scoring and historical backtesting."
)


# --------------------------------------------------
# Load persistent watchlist
# --------------------------------------------------
watchlist = load_watchlist()


# --------------------------------------------------
# Sidebar controls
# --------------------------------------------------
with st.sidebar:
    st.header("Scanner Controls")

    minimum_score = st.slider(
        label="Minimum score",
        min_value=0,
        max_value=100,
        value=70,
        step=5,
    )

    signal_filter = st.selectbox(
        label="Trading signal",
        options=["All", "BUY", "SELL", "HOLD"],
    )

    ticker_search = st.text_input(
        label="Search ticker",
        placeholder="Example: AAPL",
    )

    run_scanner = st.button(
        label="🚀 Scan Market",
        type="primary",
        width="stretch",
    )

    st.divider()
    st.subheader("⭐ My Watchlist")

    if watchlist:
        for saved_ticker in watchlist:
            watch_col, remove_col = st.columns([3, 1])

            watch_col.write(saved_ticker)

            if remove_col.button(
                "✕",
                key=f"remove_{saved_ticker}",
                help=f"Remove {saved_ticker}",
            ):
                remove_stock(
                    watchlist,
                    saved_ticker,
                )
                st.rerun()
    else:
        st.caption("No saved stocks.")


# --------------------------------------------------
# Run the market scanner
# --------------------------------------------------
if run_scanner:
    scan_start = time.perf_counter()

    with st.spinner(
        "Loading S&P 500 ticker symbols...",
        show_time=True,
    ):
        stocks = download_sp500_tickers(
            SP500_URL,
            TICKER_FILE,
        )

    if not stocks:
        st.error("No ticker symbols could be loaded.")
        st.stop()

    with st.spinner(
        f"Scanning {len(stocks)} stocks...",
        show_time=True,
    ):
        df, chart_data = scan_stocks(stocks)

    scan_time = time.perf_counter() - scan_start

    if df.empty:
        st.error("The scanner did not generate any results.")
        st.stop()

    # Store results so filters and buttons do not trigger a new scan.
    st.session_state["scan_results"] = df
    st.session_state["chart_data"] = chart_data
    st.session_state["scan_time"] = scan_time

    st.success(
        f"Market scan complete — {len(df)} stocks analysed."
    )


# --------------------------------------------------
# Display stored scan results
# --------------------------------------------------
if "scan_results" in st.session_state:
    df = st.session_state["scan_results"]
    chart_data = st.session_state["chart_data"]
    scan_time = st.session_state["scan_time"]

    # --------------------------------------------------
    # Market overview and pulse
    # --------------------------------------------------
    st.subheader("Market Overview")

    display_market_overview(
        df,
        scan_time,
    )

    st.divider()

    display_market_pulse(df)

    st.divider()

    # --------------------------------------------------
    # Apply filters
    # --------------------------------------------------
    filtered_df = apply_stock_filters(
        df=df,
        minimum_score=minimum_score,
        signal_filter=signal_filter,
        ticker_search=ticker_search,
    )

    # --------------------------------------------------
    # Best opportunity
    # --------------------------------------------------
    st.subheader("🏆 Best Opportunity")

    if filtered_df.empty:
        st.warning(
            "No stocks match the current filters. "
            "Try lowering the minimum score."
        )

    else:
        best_stock = filtered_df.iloc[0]

        display_best_opportunity(best_stock)

        if best_stock["Ticker"] not in watchlist:
            if st.button(
                "⭐ Add Best Opportunity to Watchlist",
                key="add_best_to_watchlist",
            ):
                add_stock(
                    watchlist,
                    best_stock["Ticker"],
                )

                st.success(
                    f'{best_stock["Ticker"]} added to your watchlist.'
                )

                st.rerun()
        else:
            st.info(
                f'{best_stock["Ticker"]} is already in your watchlist.'
            )

        st.divider()

        # --------------------------------------------------
        # Interactive stock chart
        # --------------------------------------------------
        st.subheader("📈 Interactive Stock Chart")

        chart_tickers = filtered_df["Ticker"].tolist()

        selected_ticker = st.selectbox(
            label="Select a stock to analyse",
            options=chart_tickers,
            index=0,
        )

        selected_data = chart_data.get(selected_ticker)

        if selected_data is None:
            st.warning(
                f"Chart data is unavailable for {selected_ticker}."
            )

        else:
            chart = create_stock_chart(
                selected_ticker,
                selected_data["open"],
                selected_data["high"],
                selected_data["low"],
                selected_data["close"],
                selected_data["volume"],
                selected_data["ma_short"],
                selected_data["ma_long"],
                selected_data["rsi"],
            )

            st.plotly_chart(
                chart,
                width="stretch",
            )

            selected_action1, selected_action2 = st.columns(2)

            with selected_action1:
                if selected_ticker not in watchlist:
                    if st.button(
                        "⭐ Add Selected Stock to Watchlist",
                        key=f"add_selected_{selected_ticker}",
                        width="stretch",
                    ):
                        add_stock(
                            watchlist,
                            selected_ticker,
                        )

                        st.success(
                            f"{selected_ticker} added to your watchlist."
                        )

                        st.rerun()
                else:
                    st.info(
                        f"{selected_ticker} is already saved."
                    )

            with selected_action2:
                st.metric(
                    label="Selected ticker",
                    value=selected_ticker,
                )

            st.divider()

            # --------------------------------------------------
            # Strategy backtest
            # --------------------------------------------------
            st.subheader("🧪 Strategy Backtest")

            starting_balance = st.number_input(
                label="Starting balance",
                min_value=1000,
                max_value=1_000_000,
                value=10_000,
                step=1000,
                key=f"backtest_balance_{selected_ticker}",
            )

            if st.button(
                "Run Backtest",
                type="primary",
                key=f"run_backtest_{selected_ticker}",
            ):
                try:
                    backtest = run_backtest(
                        open_prices=selected_data["open"],
                        close_prices=selected_data["close"],
                        ma_short=selected_data["ma_short"],
                        ma_long=selected_data["ma_long"],
                        starting_balance=starting_balance,
                    )

                    st.success(
                        f"Backtest completed for {selected_ticker}."
                    )

                    result1, result2, result3 = st.columns(3)
                    result4, result5, result6 = st.columns(3)

                    result1.metric(
                        label="Ending Balance",
                        value=f'${backtest["Ending Balance"]:,.2f}',
                    )

                    result2.metric(
                        label="Strategy Return",
                        value=(
                            f'{backtest["Strategy Return (%)"]:.2f}%'
                        ),
                    )

                    result3.metric(
                        label="Buy & Hold Return",
                        value=(
                            f'{backtest["Buy and Hold Return (%)"]:.2f}%'
                        ),
                    )

                    result4.metric(
                        label="Outperformance",
                        value=(
                            f'{backtest["Outperformance (%)"]:.2f}%'
                        ),
                    )

                    result5.metric(
                        label="Win Rate",
                        value=f'{backtest["Win Rate (%)"]:.1f}%',
                    )

                    result6.metric(
                        label="Maximum Drawdown",
                        value=(
                            f'{backtest["Maximum Drawdown (%)"]:.1f}%'
                        ),
                    )

                    st.write(
                        "Number of completed trades: "
                        f'{backtest["Number of Trades"]}'
                    )

                    equity_curve = backtest["Equity Curve"]

                    if not equity_curve.empty:
                        st.subheader("Portfolio Equity Curve")

                        st.line_chart(
                            equity_curve,
                            width="stretch",
                        )

                    trade_log = backtest["Trade Log"]

                    if not trade_log.empty:
                        st.subheader("Trade History")

                        st.dataframe(
                            trade_log,
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "No completed crossover trades occurred "
                            "during this period."
                        )

                except Exception as error:
                    st.error(
                        f"Backtest failed: {error}"
                    )

        st.divider()

        # --------------------------------------------------
        # Opportunities and favourites table
        # --------------------------------------------------
        st.subheader(
            f"🔥 Opportunities ({len(filtered_df)} matches)"
        )

        st.caption(
            "Tick or untick stocks, then press "
            "**Save Favourites**."
        )

        favourite_df, edited_df = display_opportunities_editor(
            filtered_df,
            watchlist,
        )

        if st.button(
            "⭐ Save Favourites",
            type="primary",
            width="stretch",
        ):
            visible_favourites = edited_df.loc[
                edited_df["Favourite"],
                "Ticker",
            ].tolist()

            visible_tickers = set(
                favourite_df["Ticker"].tolist()
            )

            hidden_favourites = [
                ticker
                for ticker in watchlist
                if ticker not in visible_tickers
            ]

            replace_watchlist(
                hidden_favourites + visible_favourites
            )

            st.success("Watchlist updated.")
            st.rerun()

        # --------------------------------------------------
        # CSV download
        # --------------------------------------------------
        csv_data = filtered_df.to_csv(index=False)

        st.download_button(
            label="📥 Download Filtered Results",
            data=csv_data,
            file_name="project_atlas_results.csv",
            mime="text/csv",
            width="stretch",
        )

else:
    st.info(
        "Use the sidebar and press **Scan Market** to begin."
    )