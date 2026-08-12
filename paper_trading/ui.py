from __future__ import annotations
import pandas as pd
import streamlit as st
from .sprint_status_ui import display_paper_trading_system_status
from .account import PaperAccountService
from .journal_ui import display_paper_journal_dashboard
from .performance_ui import display_performance_dashboard
from .risk_ui import display_risk_manager
from .portfolio_ui import display_live_portfolio_dashboard
from .trading_ui import display_order_history, display_order_ticket

def display_paper_trading_dashboard(db_path="data/paper_trading.db", market_df: pd.DataFrame | None=None):
    st.header("💼 Atlas Paper Trading")
    service = PaperAccountService(db_path)
    account = service.initialise_account()

    if market_df is not None and not market_df.empty and "Ticker" in market_df.columns:
        price_col = next((c for c in ("Close","Current Price","Price") if c in market_df.columns), None)
        if price_col:
            prices = dict(zip(
                market_df["Ticker"].astype(str).str.upper(),
                pd.to_numeric(market_df[price_col], errors="coerce"),
            ))
            service.update_market_prices({
                t: float(p) for t,p in prices.items() if pd.notna(p) and float(p) > 0
            })

    trade_tab, portfolio_tab, history_tab, account_tab = st.tabs(
        ["🛒 Trade","📊 Portfolio","📋 History","⚙ Account"]
    )
    with trade_tab:
        display_order_ticket(market_df=market_df, db_path=db_path)
    with portfolio_tab:
        display_live_portfolio_dashboard(db_path=db_path)
    with history_tab:
        display_order_history(db_path=db_path)
    with account_tab:
        account = service.active_account()
        snap = service.snapshot(persist=True)
        cols = st.columns(4)
        for col,(label,value) in zip(cols,[
            ("Starting Balance",f"${account.starting_balance:,.2f}"),
            ("Current Equity",f"${snap.equity:,.2f}"),
            ("Cash",f"${snap.cash:,.2f}"),
            ("Total Return",f"{snap.total_return_pct:.2%}"),
        ]):
            col.metric(label,value)
        with st.expander("Reset Paper Account", expanded=True):
            balance = st.number_input("New starting balance", min_value=100.0, value=float(account.starting_balance), step=1000.0)
            confirm = st.text_input('Type "RESET" to confirm')
            if st.button("Reset Paper Account"):
                if confirm != "RESET":
                    st.error('Type "RESET" exactly.')
                else:
                    service.reset_account(account.name, balance)
                    st.success("Paper account reset.")
                    st.rerun()
