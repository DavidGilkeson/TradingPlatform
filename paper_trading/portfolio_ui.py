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

    st.subheader("📊 Portfolio & Positions")
    st.caption("Manage open paper positions with the information that matters most: allocation, live P&L and exit-plan context.")
    row1 = st.columns(5)
    for col, (label, value) in zip(row1, [
        ("Account Equity", f"${analytics.equity:,.2f}"), ("Cash", f"${analytics.cash:,.2f}"),
        ("Invested", f"${analytics.invested_value:,.2f}"), ("Unrealised P&L", f"${analytics.unrealised_pnl:,.2f}"),
        ("Open Positions", analytics.open_positions)]): col.metric(label, value)

    if frame.empty:
        st.info("No open positions yet. Your first paper BUY will appear here with live P&L and exit-plan context.")
        return

    st.markdown("### Open Positions")
    display = frame.copy()
    display["Shares"] = display["Shares"].map(lambda x: f"{x:,.4f}")
    for c in ["Average Entry","Current Price","Cost Basis","Market Value","Unrealised P&L"]:
        display[c] = display[c].map(lambda x: f"${x:,.2f}")
    display["Return"] = display["Return"].map(lambda x: f"{x:.2%}")
    display["Allocation"] = display["Allocation"].map(lambda x: f"{x:.1%}")
    st.dataframe(display, width="stretch", hide_index=True)

    winner, loser = st.columns(2)
    with winner:
        st.success(f"Largest winner: **{analytics.largest_winner_ticker} {analytics.largest_winner_return:.2%}**" if analytics.largest_winner_ticker else "No winning positions currently.")
    with loser:
        st.warning(f"Largest loser: **{analytics.largest_loser_ticker} {analytics.largest_loser_return:.2%}**" if analytics.largest_loser_ticker else "No losing positions currently.")

    st.markdown("### Position Manager")
    ticker = st.selectbox("Position", frame["Ticker"].tolist(), key="paper_position_details_ticker")
    details = get_position_details(service, ticker)
    if not details: return
    st.markdown(f"#### {ticker} — {details['status']}")
    st.caption(details["status_detail"])
    a,b,c,d,e = st.columns(5)
    a.metric("Shares", f"{details['shares']:,.4f}")
    b.metric("Avg Entry", f"${details['average_entry_price']:,.2f}")
    c.metric("Current", f"${details['current_price']:,.2f}", f"{details['unrealised_return_pct']:.2%}")
    d.metric("Unrealised P&L", f"${details['unrealised_pnl']:,.2f}")
    e.metric("Allocation", f"{details['allocation_pct']:.1%}")

    plan, context = st.columns(2)
    with plan:
        st.markdown("#### Exit Plan")
        stop = details.get("stop_price"); target = details.get("target_price")
        if stop is None and target is None:
            st.info("No stop/target plan saved for this position yet.")
        else:
            x,y,z = st.columns(3)
            x.metric("Stop", f"${stop:,.2f}" if stop is not None else "—")
            y.metric("Target", f"${target:,.2f}" if target is not None else "—")
            z.metric("Planned R:R", f"{details['reward_risk_ratio']:.2f}:1" if details.get('reward_risk_ratio') is not None else "—")
            if details.get("distance_to_stop_pct") is not None: st.caption(f"Distance above stop: {details['distance_to_stop_pct']:.2%}")
            if details.get("distance_to_target_pct") is not None: st.caption(f"Distance to target: {details['distance_to_target_pct']:.2%}")
    with context:
        st.markdown("#### Original Trade Context")
        journal = details.get("latest_journal") or {}
        st.write(f"**Reason:** {journal.get('reason') or '—'}")
        st.write(f"**Confidence:** {journal.get('confidence') or '—'}")
        st.write(f"**Atlas Score:** {journal.get('atlas_score') or '—'}")
        st.write(f"**Notes:** {journal.get('notes') or '—'}")

    st.caption("Use the Trade tab to add/reduce/close a position and the exit-plan tools to update stop or target levels.")

    charts = st.expander("Portfolio allocation charts", expanded=False)
    with charts:
        left,right=st.columns(2)
        with left:
            st.plotly_chart(px.pie(frame,names="Ticker",values="Market Value",hole=.45,title="Position Allocation"),width="stretch")
        with right:
            cash_df=pd.DataFrame({"Category":["Cash","Invested"],"Value":[analytics.cash,analytics.invested_value]})
            st.plotly_chart(px.pie(cash_df,names="Category",values="Value",hole=.45,title="Cash vs Invested"),width="stretch")
