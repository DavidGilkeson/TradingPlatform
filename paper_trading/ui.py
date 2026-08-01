"""Complete Streamlit dashboard for Atlas paper trading."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .account import PaperAccountService
from .trading_ui import display_order_history, display_order_ticket


def display_paper_trading_dashboard(
    db_path: str = "data/paper_trading.db",
    market_df: pd.DataFrame | None = None,
) -> None:
    """Display account metrics, order entry, positions, and history."""

    st.header("💼 Atlas Paper Trading")
    st.caption(
        "Practice trade execution and portfolio management without risking "
        "real money."
    )

    service = PaperAccountService(db_path)
    account = service.initialise_account()

    if market_df is not None and not market_df.empty and "Ticker" in market_df.columns:
        price_column = next(
            (
                column
                for column in ("Close", "Current Price", "Price")
                if column in market_df.columns
            ),
            None,
        )
        if price_column:
            prices = dict(
                zip(
                    market_df["Ticker"].astype(str).str.upper(),
                    pd.to_numeric(market_df[price_column], errors="coerce"),
                )
            )
            prices = {
                ticker: float(price)
                for ticker, price in prices.items()
                if pd.notna(price) and float(price) > 0
            }
            service.update_market_prices(prices)

    snapshot = service.snapshot(persist=True)
    account = service.active_account()

    row = st.columns(6)
    metrics = [
        ("Cash", f"${snapshot.cash:,.2f}"),
        ("Buying Power", f"${account.buying_power:,.2f}"),
        ("Portfolio Value", f"${snapshot.positions_value:,.2f}"),
        ("Account Equity", f"${snapshot.equity:,.2f}"),
        ("Total Return", f"{snapshot.total_return_pct:.2%}"),
        ("Open Positions", snapshot.open_positions),
    ]
    for column, (label, value) in zip(row, metrics):
        column.metric(label, value)

    pnl_row = st.columns(2)
    pnl_row[0].metric("Unrealised P&L", f"${snapshot.unrealised_pnl:,.2f}")
    pnl_row[1].metric("Realised P&L", f"${snapshot.realised_pnl:,.2f}")

    trade_tab, positions_tab, history_tab = st.tabs(
        ["🛒 Trade", "📈 Positions", "📋 History"]
    )

    with trade_tab:
        display_order_ticket(
            market_df=market_df,
            db_path=db_path,
        )

    with positions_tab:
        positions = service.repository.list_positions(account.id)

        if not positions:
            st.info("No open paper positions.")
        else:
            frame = pd.DataFrame(
                [
                    {
                        "Ticker": position.ticker,
                        "Shares": position.shares,
                        "Average Entry": position.average_entry_price,
                        "Current Price": position.current_price,
                        "Market Value": position.market_value,
                        "Unrealised P&L": position.unrealised_pnl,
                        "Return": position.unrealised_return_pct,
                    }
                    for position in positions
                ]
            )

            st.dataframe(
                frame,
                width="stretch",
                hide_index=True,
                column_config={
                    "Shares": st.column_config.NumberColumn(format="%.4f"),
                    "Average Entry": st.column_config.NumberColumn(format="$%.2f"),
                    "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Market Value": st.column_config.NumberColumn(format="$%.2f"),
                    "Unrealised P&L": st.column_config.NumberColumn(format="$%.2f"),
                    "Return": st.column_config.NumberColumn(format="%.2f%%"),
                },
            )

    with history_tab:
        display_order_history(db_path=db_path)

    with st.expander("Reset Paper Account"):
        st.warning(
            "Resetting permanently removes all paper positions, orders, trades, "
            "journal entries, and account history."
        )
        reset_balance = st.number_input(
            "New starting balance",
            min_value=100.0,
            value=float(account.starting_balance),
            step=1_000.0,
            key="paper_reset_balance",
        )
        confirmation = st.text_input(
            'Type "RESET" to confirm',
            key="paper_reset_confirmation",
        )

        if st.button(
            "Reset Paper Account",
            type="secondary",
            key="reset_paper_account",
        ):
            if confirmation != "RESET":
                st.error('Type "RESET" exactly before resetting.')
            else:
                service.reset_account(
                    name=account.name,
                    starting_balance=reset_balance,
                )
                st.success("Paper account reset.")
                st.rerun()

    st.caption(
        "Paper trading is simulated. It does not guarantee future live-trading "
        "performance."
    )
