import streamlit as st
from .account import PaperAccountService
from .trading_intelligence import (
    derive_intelligence_summary,
    performance_by_atlas_score,
    performance_by_confidence,
    performance_by_ticker,
    performance_by_verdict,
)

def display_trading_intelligence(*, db_path="data/paper_trading.db"):
    service=PaperAccountService(db_path)
    st.subheader("🧠 Atlas Trading Intelligence")
    st.caption("Learn from completed paper trades and compare which observed setups have performed best so far.")
    minimum_trades=st.number_input("Minimum trades per pattern",min_value=1,max_value=100,value=1,step=1,key="intelligence_minimum_trades")
    summary=derive_intelligence_summary(service,minimum_trades=int(minimum_trades))
    if summary.total_trades==0:
        st.info("Atlas needs completed paper trades before it can identify performance patterns.")
        return
    cols=st.columns(4)
    cols[0].metric("Completed Trades",summary.total_trades)
    cols[1].metric("Best Score Band",summary.best_atlas_score_band or "—")
    cols[2].metric("Best Confidence","—" if summary.best_confidence_level is None else f"{summary.best_confidence_level:.0f}/10")
    cols[3].metric("Best Ticker",summary.best_ticker or "—")
    if summary.strongest_pattern: st.success(summary.strongest_pattern)
    st.warning("These are observations from paper-trading history, not proof that a pattern will continue.")

    tabs=st.tabs(["By Ticker","By Atlas Score","By Confidence","By Verdict/Reason"])
    frames=[
        performance_by_ticker(service,int(minimum_trades)),
        performance_by_atlas_score(service,int(minimum_trades)),
        performance_by_confidence(service,int(minimum_trades)),
        performance_by_verdict(service,int(minimum_trades)),
    ]
    for tab,frame in zip(tabs,frames):
        with tab:
            if frame.empty: st.info("No pattern meets the minimum trade count.")
            else: st.dataframe(frame,width="stretch",hide_index=True)
