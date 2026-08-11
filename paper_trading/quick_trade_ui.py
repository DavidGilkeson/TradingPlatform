from __future__ import annotations
import pandas as pd
import streamlit as st
from .one_click import best_reason_from_row, queue_paper_trade
from .trade_integration import prepare_quick_trade_candidates

def display_selected_quick_trade(frame, *, source, key_prefix, heading="⚡ Quick Paper Trade", minimum_score=None):
    candidates=prepare_quick_trade_candidates(frame,minimum_score=minimum_score,limit=10)
    if candidates.empty:
        return
    st.markdown(f"#### {heading}")
    ticker=st.selectbox("Ticker",candidates["Ticker"].tolist(),key=f"{key_prefix}_ticker")
    row=candidates[candidates["Ticker"]==ticker].iloc[0]
    reason=best_reason_from_row(row)
    if st.button(f"Queue {ticker} Paper Buy",key=f"{key_prefix}_{ticker}",width="stretch"):
        queue_paper_trade(ticker=ticker,side="BUY",reason=reason,notes=f"Queued from {source}",shares=1.0)
        st.success(f"{ticker} queued from {source}. Open Paper Trading to review and confirm the simulated order.")
