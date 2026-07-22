"""
app.py

Main Streamlit dashboard for Project Atlas.

Features:
- S&P 500 market scanner
- Persistent scan caching
- Market analytics dashboard
- Score, signal and ticker filters
- Professional stock analysis report
- Interactive Plotly charts
- Moving-average strategy backtesting
- Persistent watchlist
- Persistent portfolio tracker
- Editable favourites
- CSV export
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
from dashboard import display_market_analytics
from portfolio import (
    display_portfolio,
    load_portfolio,
)
from scanner import scan_stocks
from strategy_comparison import (
    display_strategy_comparison,
)
from trade_journal import (
    display_trade_journal,
    load_trade_journal,
)
from ui_components import (
    apply_stock_filters,
    display_best_opportunity,
    display_market_overview,
    display_market_pulse,
    display_opportunities_editor,
)
from utils import download_sp500_tickers
from historical_scans import (
    display_historical_trends,
    save_historical_scan,
)
from opportunity_center import display_opportunity_center
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
# Load persistent data
# --------------------------------------------------
watchlist = load_watchlist()
portfolio = load_portfolio()
trade_journal = load_trade_journal()
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
        options=[
            "All",
            "BUY",
            "SELL",
            "HOLD",
        ],
    )

    ticker_search = st.text_input(
        label="Search ticker",
        placeholder="Example: AAPL",
    )

    use_cache = st.checkbox(
        label="Use recent cached scan",
        value=True,
        help=("Reuse saved market data when the cached scan is still fresh."),
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
            st.caption(
                f"Last saved: {cache_timestamp.strftime('%d %b %Y, %I:%M:%S %p')}"
            )

        if cache_age_seconds is not None:
            cache_age_minutes = cache_age_seconds / 60

            st.caption(f"Cache age: {cache_age_minutes:.1f} minutes")

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

        session_keys = [
            "scan_results",
            "chart_data",
            "scan_time",
            "data_source",
            "cache_age_seconds",
        ]

        for key in session_keys:
            st.session_state.pop(key, None)

        if cache_cleared:
            st.success("Cached market scan cleared.")
        else:
            st.error("The cache could not be cleared.")

        st.rerun()

    # --------------------------------------------------
    # Watchlist
    # --------------------------------------------------
    st.divider()
    st.subheader("⭐ My Watchlist")

    if watchlist:
        for saved_ticker in watchlist:
            ticker_column, remove_column = st.columns([3, 1])

            ticker_column.write(saved_ticker)

            if remove_column.button(
                "✕",
                key=f"remove_watchlist_{saved_ticker}",
                help=f"Remove {saved_ticker}",
            ):
                removed = remove_stock(
                    watchlist,
                    saved_ticker,
                )

                if removed is False:
                    st.error(f"{saved_ticker} could not be removed.")

                st.rerun()

    else:
        st.caption("No saved stocks.")


# --------------------------------------------------
# Run market scanner
# --------------------------------------------------
if run_scanner:
    cached_scan = load_market_cache() if use_cache else None

    # --------------------------------------------------
    # Load cache
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
        st.session_state["cache_age_seconds"] = cache_age_seconds

    # --------------------------------------------------
    # Run fresh scan
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
            st.error("The scanner did not generate any results.")
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

        try:
            historical_scan_id = save_historical_scan(
                df=df,
                scan_duration_seconds=scan_time,
            )

            if historical_scan_id is not None:
                st.session_state["historical_scan_id"] = historical_scan_id

        except Exception as error:
            st.warning(
                "The scan completed, but Atlas could not save the historical "
                f"snapshot: {error}"
            )

        if not cache_saved:
            st.warning("The scan completed, but Atlas could not save the market cache.")


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
        0.0,
    )

    data_source = st.session_state.get(
        "data_source",
        "session",
    )

    cache_age_seconds = st.session_state.get(
        "cache_age_seconds",
        0.0,
    )

    # --------------------------------------------------
    # Data-source status
    # --------------------------------------------------
    if data_source == "cache":
        cache_age_minutes = cache_age_seconds / 60

        st.info(
            f"⚡ Using cached market data — "
            f"{len(df)} stocks loaded, "
            f"{cache_age_minutes:.1f} minutes old."
        )

    elif data_source == "live":
        st.success(f"🟢 Fresh market scan complete — {len(df)} stocks analysed.")

    else:
        st.info(
            f"Using market data stored in this session — {len(df)} stocks available."
        )

    # --------------------------------------------------
    # Apply sidebar filters
    # --------------------------------------------------
    filtered_df = apply_stock_filters(
        df=df,
        minimum_score=minimum_score,
        signal_filter=signal_filter,
        ticker_search=ticker_search,
    )

    # --------------------------------------------------
    # Main navigation
    # --------------------------------------------------
    (
        market_tab,
        opportunity_tab,
        trends_tab,
        analysis_tab,
        portfolio_tab,
        journal_tab,
        strategy_tab,
    ) = st.tabs(
        [
            "📊 Market",
            "🎯 Opportunity Centre",
            "🕒 Atlas Trends",
            "🔎 Stock Analysis",
            "💼 Portfolio",
            "📓 Trade Journal",
            "🧪 Strategy Lab",
        ]
    )

    # ==================================================
    # MARKET TAB
    # ==================================================
    with market_tab:
        st.header("Market Dashboard")

        display_market_overview(
            df,
            scan_time,
        )

        st.divider()

        display_market_pulse(df)

        st.divider()

        display_market_analytics(df)

        st.divider()

        # --------------------------------------------------
        # Filtered opportunities
        # --------------------------------------------------
        st.header("Filtered Opportunities")

        st.caption(
            f"Minimum score: {minimum_score} | "
            f"Signal: {signal_filter} | "
            f"Matches: {len(filtered_df)}"
        )

        if filtered_df.empty:
            st.warning(
                "No stocks match the current filters. "
                "Try lowering the minimum score, changing "
                "the signal filter or clearing the ticker search."
            )

        else:
            # --------------------------------------------------
            # Best opportunity
            # --------------------------------------------------
            st.subheader("🏆 Best Opportunity")

            best_stock = filtered_df.iloc[0]

            display_best_opportunity(best_stock)

            best_ticker = str(best_stock["Ticker"])

            if best_ticker not in watchlist:
                if st.button(
                    "⭐ Add Best Opportunity to Watchlist",
                    key="add_best_to_watchlist",
                    width="stretch",
                ):
                    saved = add_stock(
                        watchlist,
                        best_ticker,
                    )

                    if saved is False:
                        st.error(f"{best_ticker} could not be saved.")
                    else:
                        st.success(f"{best_ticker} added to your watchlist.")

                    st.rerun()

            else:
                st.info(f"{best_ticker} is already in your watchlist.")

            st.divider()

            # --------------------------------------------------
            # Opportunities and favourites
            # --------------------------------------------------
            st.subheader(f"🔥 Opportunities ({len(filtered_df)} matches)")

            st.caption(
                "Tick or untick stocks and press "
                "**Save Favourites** to update your watchlist."
            )

            favourite_df, edited_df = display_opportunities_editor(
                filtered_df,
                watchlist,
            )

            if st.button(
                "⭐ Save Favourites",
                type="primary",
                key="save_favourites",
                width="stretch",
            ):
                visible_favourites = edited_df.loc[
                    edited_df["Favourite"],
                    "Ticker",
                ].tolist()

                visible_tickers = set(favourite_df["Ticker"].tolist())

                hidden_favourites = [
                    ticker for ticker in watchlist if ticker not in visible_tickers
                ]

                updated_watchlist = list(
                    dict.fromkeys(hidden_favourites + visible_favourites)
                )

                saved = replace_watchlist(updated_watchlist)

                if saved is False:
                    st.error("The watchlist could not be updated.")
                else:
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

    # ==================================================
    # ATLAS TRENDS TAB
    # ==================================================
    with trends_tab:
        display_historical_trends(current_df=df)

    # ==================================================
    # STOCK ANALYSIS TAB
    # ==================================================
    with analysis_tab:
        st.header("Stock Analysis")

        if filtered_df.empty:
            st.warning(
                "No stocks match the current sidebar filters. "
                "Adjust the filters to select a stock."
            )

        else:
            analysis_tickers = filtered_df["Ticker"].astype(str).tolist()

            selected_ticker = st.selectbox(
                label="Select a stock to analyse",
                options=analysis_tickers,
                index=0,
                key="analysis_ticker",
            )

            selected_stock_matches = filtered_df.loc[
                filtered_df["Ticker"].astype(str) == selected_ticker
            ]

            if selected_stock_matches.empty:
                st.error(f"Analysis results could not be found for {selected_ticker}.")

            else:
                selected_stock = selected_stock_matches.iloc[0]

                selected_data = chart_data.get(selected_ticker)

                # --------------------------------------------------
                # Professional analysis report
                # --------------------------------------------------
                display_stock_analysis(selected_stock)

                st.divider()

                # --------------------------------------------------
                # Interactive chart
                # --------------------------------------------------
                st.subheader("📈 Interactive Stock Chart")

                if selected_data is None:
                    st.warning(f"Chart data is unavailable for {selected_ticker}.")

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

                        action_column, ticker_column = st.columns(2)

                        with action_column:
                            if selected_ticker not in watchlist:
                                if st.button(
                                    "⭐ Add Selected Stock to Watchlist",
                                    key=(f"add_selected_{selected_ticker}"),
                                    width="stretch",
                                ):
                                    saved = add_stock(
                                        watchlist,
                                        selected_ticker,
                                    )

                                    if saved is False:
                                        st.error(
                                            f"{selected_ticker} could not be saved."
                                        )
                                    else:
                                        st.success(
                                            f"{selected_ticker} "
                                            "added to your watchlist."
                                        )

                                    st.rerun()

                            else:
                                st.info(f"{selected_ticker} is already saved.")

                        with ticker_column:
                            st.metric(
                                label="Selected ticker",
                                value=selected_ticker,
                            )

                        st.divider()

                        # --------------------------------------------------
                        # Backtesting
                        # --------------------------------------------------
                        st.subheader("🧪 Strategy Backtest")

                        starting_balance = st.number_input(
                            label="Starting balance",
                            min_value=1000,
                            max_value=1_000_000,
                            value=10_000,
                            step=1000,
                            key=(f"backtest_balance_{selected_ticker}"),
                        )

                        if st.button(
                            "Run Backtest",
                            type="primary",
                            key=(f"run_backtest_{selected_ticker}"),
                            width="stretch",
                        ):
                            try:
                                backtest = run_backtest(
                                    open_prices=(selected_data["open"]),
                                    close_prices=(selected_data["close"]),
                                    ma_short=(selected_data["ma_short"]),
                                    ma_long=(selected_data["ma_long"]),
                                    starting_balance=(starting_balance),
                                )

                                st.success(f"Backtest completed for {selected_ticker}.")

                                metric1, metric2, metric3 = st.columns(3)

                                metric4, metric5, metric6 = st.columns(3)

                                metric1.metric(
                                    label="Ending Balance",
                                    value=(f"${backtest['Ending Balance']:,.2f}"),
                                )

                                metric2.metric(
                                    label="Strategy Return",
                                    value=(f"{backtest['Strategy Return (%)']:.2f}%"),
                                )

                                metric3.metric(
                                    label="Buy & Hold Return",
                                    value=(
                                        f"{backtest['Buy and Hold Return (%)']:.2f}%"
                                    ),
                                )

                                metric4.metric(
                                    label="Outperformance",
                                    value=(f"{backtest['Outperformance (%)']:.2f}%"),
                                )

                                metric5.metric(
                                    label="Win Rate",
                                    value=(f"{backtest['Win Rate (%)']:.1f}%"),
                                )

                                metric6.metric(
                                    label="Maximum Drawdown",
                                    value=(f"{backtest['Maximum Drawdown (%)']:.1f}%"),
                                )

                                st.write(
                                    "Number of completed trades: "
                                    f"{backtest['Number of Trades']}"
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
                                        "No completed crossover "
                                        "trades occurred during "
                                        "this period."
                                    )

                            except Exception as error:
                                st.error(f"Backtest failed: {error}")

    # ==================================================
    # PORTFOLIO TAB
    # ==================================================
    with portfolio_tab:
        display_portfolio(
            portfolio=portfolio,
            df=df,
        )
    # ==================================================
    # TRADE JOURNAL TAB
    # ==================================================
    with journal_tab:
        display_trade_journal(
            trades=trade_journal,
        )
    # ==================================================
    # STRATEGY COMPARISON TAB
    # ==================================================
    with strategy_tab:
        st.header("Strategy Lab")

        if filtered_df.empty:
            st.warning(
                "No stocks match the current sidebar filters. "
                "Adjust the filters before comparing strategies."
            )

        else:
            strategy_tickers = filtered_df["Ticker"].astype(str).tolist()

            strategy_ticker = st.selectbox(
                label="Select a stock",
                options=strategy_tickers,
                index=0,
                key="strategy_comparison_ticker",
            )

            strategy_data = chart_data.get(strategy_ticker)

            if strategy_data is None:
                st.warning(
                    f"Historical price data is unavailable for {strategy_ticker}."
                )

            else:
                display_strategy_comparison(
                    ticker=strategy_ticker,
                    selected_data=strategy_data,
                )
    # ==================================================
    # OPPORTUNITY CENTRE TAB
    # ==================================================
    with opportunity_tab:
        display_opportunity_center(df)

else:
    st.info("Use the sidebar and press **Scan Market** to begin.")
