from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st
from .account import PaperAccountService
from .portfolio_analytics import build_positions_frame, calculate_portfolio_analytics, get_position_details

def display_live_portfolio_dashboard(*, db_path="data/paper_trading.db"):
    service = PaperAccountService(db_path)
    analytics = calculate_portfolio_analytics(service)
    frame = build_positions_frame(service)

    st.subheader("📊 Live Portfolio Dashboard")
    row1 = st.columns(5)
    values1 = [
        ("Account Equity", f"${analytics.equity:,.2f}"),
        ("Cash", f"${analytics.cash:,.2f}"),
        ("Invested", f"${analytics.invested_value:,.2f}"),
        ("Total Return", f"{analytics.total_return_pct:.2%}"),
        ("Open Positions", analytics.open_positions),
    ]
    for col, (label, value) in zip(row1, values1):
        col.metric(label, value)

    row2 = st.columns(5)
    values2 = [
        ("Unrealised P&L", f"${analytics.unrealised_pnl:,.2f}"),
        ("Realised P&L", f"${analytics.realised_pnl:,.2f}"),
        ("Winning Positions", analytics.winning_positions),
        ("Losing Positions", analytics.losing_positions),
        ("Diversification", f"{analytics.diversification_score:.0f}/100"),
    ]
    for col, (label, value) in zip(row2, values2):
        col.metric(label, value)

    if frame.empty:
        st.info("No open positions yet. Place a paper BUY order first.")
        return

    st.subheader("📈 Open Positions")
    st.dataframe(frame, width="stretch", hide_index=True)

    left, right = st.columns(2)
    with left:
        if analytics.largest_winner_ticker:
            st.success(f"**Largest Winner:** {analytics.largest_winner_ticker} {analytics.largest_winner_return:.2%}")
        else:
            st.info("No winning positions currently.")
    with right:
        if analytics.largest_loser_ticker:
            st.warning(f"**Largest Loser:** {analytics.largest_loser_ticker} {analytics.largest_loser_return:.2%}")
        else:
            st.info("No losing positions currently.")

    chart1, chart2 = st.columns(2)
    with chart1:
        fig = px.pie(frame, names="Ticker", values="Market Value", hole=0.45, title="Position Allocation")
        st.plotly_chart(fig, width="stretch")
    with chart2:
        cash_df = pd.DataFrame({"Category":["Cash","Invested"],"Value":[analytics.cash,analytics.invested_value]})
        fig = px.pie(cash_df, names="Category", values="Value", hole=0.45, title="Cash vs Invested")
        st.plotly_chart(fig, width="stretch")

    st.subheader("🔎 Position Details")
    ticker = st.selectbox("Select a position", frame["Ticker"].tolist(), key="paper_position_details_ticker")
    details = get_position_details(service, ticker)
    if details:
        metrics = st.columns(4)
        metrics[0].metric("Shares", f"{details['shares']:,.4f}")
        metrics[1].metric("Average Entry", f"${details['average_entry_price']:,.2f}")
        metrics[2].metric("Current Price", f"${details['current_price']:,.2f}")
        metrics[3].metric("Unrealised Return", f"{details['unrealised_return_pct']:.2%}")
        order, journal = details["latest_order"], details["latest_journal"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Latest Trade Context")
            if order:
                st.write(f"**Side:** {order.get('side','—')}")
                st.write(f"**Filled price:** ${float(order.get('filled_price') or 0):,.2f}")
                st.write(f"**Date:** {order.get('filled_at') or order.get('created_at')}")
        with c2:
            st.markdown("#### Journal Evidence")
            if journal:
                st.write(f"**Reason:** {journal.get('reason') or '—'}")
                st.write(f"**Confidence:** {journal.get('confidence') or '—'}")
                st.write(f"**Atlas Score:** {journal.get('atlas_score') or '—'}")
                st.write(f"**Notes:** {journal.get('notes') or '—'}")
