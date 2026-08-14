"""Forward Testing workspace."""
import streamlit as st
from .account import PaperAccountService
from .forward_testing import ForwardTestRepository, forward_test_summary

def display_forward_testing(*,db_path="data/paper_trading.db"):
    st.subheader("🧪 Forward Testing")
    st.caption("Record Atlas opportunities prospectively before their outcomes are known.")
    service=PaperAccountService(db_path); account=service.active_account()
    repo=ForwardTestRepository(db_path)

    with st.expander("Record Forward-Test Decision",expanded=True):
        a,b=st.columns(2)
        with a:
            ticker=st.text_input("Ticker",key="ft_ticker").upper().strip()
            decision=st.selectbox("Decision",["WATCH","TAKEN","SKIPPED"],key="ft_decision")
            score=st.number_input("Atlas Score",0.0,100.0,70.0,1.0,key="ft_score")
        with b:
            confidence=st.number_input("Confidence",0.0,10.0,5.0,1.0,key="ft_confidence")
            price=st.number_input("Market Price",min_value=0.0,value=0.0,step=0.01,key="ft_price")
            signal=st.text_input("Signal",key="ft_signal")
        reason=st.text_area("Why take, skip or watch this setup?",key="ft_reason")
        if st.button("Save Forward-Test Decision",type="primary",key="ft_save"):
            if not ticker: st.error("Enter a ticker first.")
            else:
                repo.record(account_id=account.id,ticker=ticker,decision=decision,
                    atlas_score=score,confidence=confidence,
                    market_price=price if price>0 else None,
                    signal=signal or None,reason=reason or None)
                st.success(f"{ticker} recorded as {decision}."); st.rerun()

    history=repo.history(account.id); x=forward_test_summary(history)
    cols=st.columns(5)
    cols[0].metric("Recorded",x["total"]); cols[1].metric("Taken",x["taken"])
    cols[2].metric("Skipped",x["skipped"]); cols[3].metric("Watching",x["watch"])
    cols[4].metric("Decision Discipline","—" if x["discipline_rate"] is None else f'{x["discipline_rate"]*100:.1f}%')
    if history.empty: st.info("No forward-test decisions recorded yet.")
    else: st.dataframe(history,width="stretch",hide_index=True)
    st.warning("Record opportunities before you know their outcome to reduce hindsight and selection bias.")
