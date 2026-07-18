"""
app.py

Streamlit dashboard for Project Atlas.

Features:
- S&P 500 market scanner
- Persistent market-data caching
- Market overview and Market Pulse
- Score, signal and ticker filters
- Best opportunity summary
- Professional stock analysis report
- Persistent watchlist
- Interactive Plotly charts
- Strategy backtesting
- Editable favourites table
- CSV download
"""

import time

import streamlit as st

from analysis import display_stock_analysis
from backtester import run_backtest
from cache.cache_manager import (
    clear_market_cache,
    get_cache_status,
    load_market_cache,
    save_market_cache,
)
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
from dashboard import display_market_analytics


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
# Load persistent watchlist and cache status
# --------------------------------------------------
watchlist = load_watchlist()
cache_status = get_cache_status()


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

    use_cache = st.checkbox(
        label="Use recent cached scan",
        value=True,
        help=(
            "Reuse market data when the saved scan is less "
            "than 15 minutes old."
        ),
    )

    run_scanner = st.button(
        label="🚀 Scan Market",
        type="primary",
        width="stretch",
    )

    # --------------------------------------------------
    # Cache status
    # --------------------------------------------------
    st.divider()
    st.subheader("⚡ Market Data Cache")

    if cache_status["exists"]:
        cache_timestamp = cache_status.get("timestamp")
        cache_age_seconds = cache_status.get("age_seconds")

        if cache_timestamp is not None:
            st.write(
                "Last saved:",
                cache_timestamp.strftime("%d %b %Y, %I:%M:%S %p"),
            )

        if cache_age_seconds is not None:
            cache_age_minutes = cache_age_seconds / 60

            st.write(
                f"Cache age: {cache_age_minutes:.1f} minutes"
            )

        if cache_status["fresh"]:
            st.success("Cached market data is fresh.")
        else:
            st.warning("Cached market data is stale.")
    else:
        st.caption("No cached market scan is available.")

    if st.button(
        "🗑 Clear Cached Scan",
        width="stretch",
    ):
        cache_cleared = clear_market_cache()

        st.session_state.pop("scan_results", None)
        st.session_state.pop("chart_data", None)
        st.session_state.pop("scan_time", None)
        st.session_state.pop("data_source", None)
        st.session_state.pop("cache_age_seconds", None)

        if cache_cleared:
            st.success("Cached market scan cleared.")
        else:
            st.error("The cached scan could not be cleared.")

        st.rerun()

    # --------------------------------------------------
    # Watchlist
    # --------------------------------------------------
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
    cached_scan = (
        load_market_cache()
        if use_cache
        else None
    )
    
    if cached_scan is None:
        st.warning("No valid cache found.")
    else:
        st.success("Cache found!")

    # --------------------------------------------------
    # Load recent cached scan
    # --------------------------------------------------
    if cached_scan is not None:
        df = cached_scan["scan_results"]
        chart_data = cached_scan["chart_data"]
        scan_time = cached_scan["scan_time"]
        cache_age_seconds = cached_scan["age_seconds"]

        st.session_state["scan_results"] = df
        st.session_state["chart_data"] = chart_data
        st.session_state["scan_time"] = scan_time
        st.session_state["data_source"] = "cache"
        st.session_state["cache_age_seconds"] = (
            cache_age_seconds
        )

        st.success(
            f"Cached market scan loaded — "
            f"{len(df)} stocks available."
        )

    # --------------------------------------------------
    # Run a fresh scan
    # --------------------------------------------------
    else:
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
            st.error(
                "The scanner did not generate any results."
            )
            st.stop()

        cache_saved = save_market_cache(
            df=df,
            chart_data=chart_data,
            scan_time=scan_time,
        )

        st.session_state["scan_results"] = df
        st.session_state["chart_data"] = chart_data
        st.session_state["scan_time"] = scan_time
        st.session_state["data_source"] = "live"
        st.session_state["cache_age_seconds"] = 0

        st.success(
            f"Live market scan complete — "
            f"{len(df)} stocks analysed."
        )

        if not cache_saved:
            st.warning(
                "The scan completed, but the results could not "
                "be saved to the cache."
            )


# --------------------------------------------------
# Display stored scan results
# --------------------------------------------------
if "scan_results" in st.session_state:
    df = st.session_state["scan_results"]
    chart_data = st.session_state.get(
        "chart_data",
        {},
    )
    scan_time = st.session_state.get(
        "scan_time",
        0,
    )

    data_source = st.session_state.get(
        "data_source",
        "session",
    )

    cache_age_seconds = st.session_state.get(
        "cache_age_seconds",
        0,
    )

    # --------------------------------------------------
    # Data-source status
    # --------------------------------------------------
    if data_source == "cache":
        cache_age_minutes = cache_age_seconds / 60

        st.info(
            f"⚡ Using cached market data from "
            f"{cache_age_minutes:.1f} minutes ago."
        )

    elif data_source == "live":
        st.success(
            "🟢 Using freshly downloaded market data."
        )

    else:
        st.info(
            "Using market data stored in the current session."
        )

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
    # Market analytics dashboard
    # --------------------------------------------------
    display_market_analytics(df)

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
    # Empty filter results
    # --------------------------------------------------
    if filtered_df.empty:
        st.warning(
            "No stocks match the current filters. "
            "Try lowering the minimum score or changing "
            "the signal filter."
        )

    else:
        # --------------------------------------------------
        # Best opportunity
        # --------------------------------------------------
        st.subheader("🏆 Best Opportunity")

        best_stock = filtered_df.iloc[0]

        display_best_opportunity(best_stock)

        if best_stock["Ticker"] not in watchlist:
            if st.button(
                "⭐ Add Best Opportunity to Watchlist",
                key="add_best_to_watchlist",
                width="stretch",
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
        # Stock selection
        # --------------------------------------------------
        st.subheader("🔎 Stock Analysis")

        chart_tickers = filtered_df["Ticker"].tolist()

        selected_ticker = st.selectbox(
            label="Select a stock to analyse",
            options=chart_tickers,
            index=0,
        )

        selected_stock_matches = filtered_df.loc[
            filtered_df["Ticker"] == selected_ticker
        ]

        if selected_stock_matches.empty:
            st.error(
                f"Analysis results could not be found "
                f"for {selected_ticker}."
            )
            st.stop()

        selected_stock = selected_stock_matches.iloc[0]

        selected_data = chart_data.get(
            selected_ticker
        )

        # --------------------------------------------------
        # Sprint 17 professional analysis report
        # --------------------------------------------------
        display_stock_analysis(selected_stock)

        st.divider()

        # --------------------------------------------------
        # Interactive stock chart
        # --------------------------------------------------
        st.subheader("📈 Interactive Stock Chart")

        if selected_data is None:
            st.warning(
                f"Chart data is unavailable for {selected_ticker}."
            )

        else:
            required_chart_fields = [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "ma_short",
                "ma_long",
                "rsi",
            ]

            missing_chart_fields = [
                field
                for field in required_chart_fields
                if field not in selected_data
            ]

            if missing_chart_fields:
                st.warning(
                    "Chart data is incomplete. Missing: "
                    + ", ".join(missing_chart_fields)
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

                selected_action1, selected_action2 = (
                    st.columns(2)
                )

                with selected_action1:
                    if selected_ticker not in watchlist:
                        if st.button(
                            "⭐ Add Selected Stock to Watchlist",
                            key=(
                                f"add_selected_"
                                f"{selected_ticker}"
                            ),
                            width="stretch",
                        ):
                            add_stock(
                                watchlist,
                                selected_ticker,
                            )

                            st.success(
                                f"{selected_ticker} added "
                                "to your watchlist."
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
                    key=(
                        f"backtest_balance_"
                        f"{selected_ticker}"
                    ),
                )

                if st.button(
                    "Run Backtest",
                    type="primary",
                    key=f"run_backtest_{selected_ticker}",
                    width="stretch",
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
                            f"Backtest completed for "
                            f"{selected_ticker}."
                        )

                        result1, result2, result3 = (
                            st.columns(3)
                        )

                        result4, result5, result6 = (
                            st.columns(3)
                        )

                        result1.metric(
                            label="Ending Balance",
                            value=(
                                f'${backtest["Ending Balance"]:,.2f}'
                            ),
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
                            value=(
                                f'{backtest["Win Rate (%)"]:.1f}%'
                            ),
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

                        equity_curve = backtest[
                            "Equity Curve"
                        ]

                        if not equity_curve.empty:
                            st.subheader(
                                "Portfolio Equity Curve"
                            )

                            st.line_chart(
                                equity_curve,
                                width="stretch",
                            )

                        trade_log = backtest[
                            "Trade Log"
                        ]

                        if not trade_log.empty:
                            st.subheader(
                                "Trade History"
                            )

                            st.dataframe(
                                trade_log,
                                width="stretch",
                                hide_index=True,
                            )
                        else:
                            st.info(
                                "No completed crossover trades "
                                "occurred during this period."
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

        favourite_df, edited_df = (
            display_opportunities_editor(
                filtered_df,
                watchlist,
            )
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

            updated_watchlist = list(
                dict.fromkeys(
                    hidden_favourites
                    + visible_favourites
                )
            )

            replace_watchlist(
                updated_watchlist
            )

            st.success("Watchlist updated.")
            st.rerun()

        # --------------------------------------------------
        # CSV download
        # --------------------------------------------------
        csv_data = filtered_df.to_csv(
            index=False
        )

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