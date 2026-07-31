import pandas as pd
import streamlit as st
from .account import PaperAccountService

def display_paper_trading_dashboard(db_path="data/paper_trading.db"):
    st.header("💼 Atlas Paper Trading")
    service = PaperAccountService(db_path)
    account = service.initialise_account()
    snap = service.snapshot()

    cols = st.columns(6)
    values = [
        ("Cash", f"${snap.cash:,.2f}"),
        ("Buying Power", f"${account.buying_power:,.2f}"),
        ("Portfolio Value", f"${snap.positions_value:,.2f}"),
        ("Equity", f"${snap.equity:,.2f}"),
        ("Total Return", f"{snap.total_return_pct:.2%}"),
        ("Open Positions", snap.open_positions),
    ]
    for col, (label, value) in zip(cols, values):
        col.metric(label, value)

    st.markdown("### Open Positions")
    positions = service.repository.list_positions(account.id)
    if not positions:
        st.info("No open positions yet. Sprint 29.2 adds BUY and SELL orders.")
    else:
        df = pd.DataFrame([{
            "Ticker": p.ticker,
            "Shares": p.shares,
            "Average Entry": p.average_entry_price,
            "Current Price": p.current_price,
            "Market Value": p.market_value,
            "Unrealised P&L": p.unrealised_pnl,
            "Return": p.unrealised_return_pct,
        } for p in positions])
        st.dataframe(df, width="stretch", hide_index=True)

    with st.expander("Reset Paper Account"):
        st.warning("This permanently removes all paper-trading data.")
        balance = st.number_input("New starting balance", min_value=100.0,
                                  value=float(account.starting_balance), step=1000.0)
        confirmation = st.text_input('Type "RESET" to confirm')
        if st.button("Reset Account"):
            if confirmation != "RESET":
                st.error('Type "RESET" exactly.')
            else:
                service.reset_account(account.name, balance)
                st.success("Paper account reset.")
                st.rerun()
