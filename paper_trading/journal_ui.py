import math
import pandas as pd
import streamlit as st
from .account import PaperAccountService
from .journal_analytics import (
    build_trade_journal_frame, calculate_journal_analytics,
    performance_by_atlas_score, performance_by_confidence
)
from .journal_review import PaperTradeReviewRepository

def _ratio(v):
    if v is None: return "—"
    if math.isinf(v): return "∞"
    return f"{v:.2f}"

def display_paper_journal_dashboard(db_path="data/paper_trading.db"):
    service=PaperAccountService(db_path)
    account=service.active_account()
    a=calculate_journal_analytics(service)
    trades=build_trade_journal_frame(service)

    st.subheader("📓 Paper Trading Journal")
    r1=st.columns(5)
    for col,(label,value) in zip(r1,[
        ("Completed Trades",a.total_trades),("Win Rate",f"{a.win_rate:.1%}"),
        ("Net P&L",f"${a.net_pnl:,.2f}"),("Profit Factor",_ratio(a.profit_factor)),
        ("Expectancy",f"${a.expectancy:,.2f}")
    ]): col.metric(label,value)

    r2=st.columns(4)
    r2[0].metric("Average Winner",f"${a.average_winner:,.2f}")
    r2[1].metric("Average Loser",f"${a.average_loser:,.2f}")
    r2[2].metric("Avg Entry Atlas Score","—" if a.average_entry_atlas_score is None else f"{a.average_entry_atlas_score:.1f}")
    r2[3].metric("Avg Confidence","—" if a.average_confidence is None else f"{a.average_confidence:.1f}/10")

    if trades.empty:
        st.info("Close a paper position to begin building journal analytics.")
        return

    st.divider()
    st.subheader("Trade History")
    c1,c2,c3=st.columns(3)
    result_filter=c1.selectbox("Result",["All","WIN","LOSS","BREAK EVEN"],key="pj_result")
    ticker_filter=c2.text_input("Ticker",key="pj_ticker")
    min_score=c3.number_input("Minimum Atlas Score",0.0,100.0,0.0,5.0,key="pj_score")

    filtered=trades.copy()
    if result_filter!="All": filtered=filtered[filtered.result==result_filter]
    if ticker_filter.strip():
        filtered=filtered[filtered.ticker.astype(str).str.contains(ticker_filter.strip(),case=False,na=False)]
    scores=pd.to_numeric(filtered.get("atlas_score"),errors="coerce")
    if scores is not None: filtered=filtered[scores.fillna(0)>=min_score]

    st.dataframe(filtered,width="stretch",hide_index=True)

    st.divider()
    st.subheader("Performance by Entry Quality")
    left,right=st.columns(2)
    with left:
        st.markdown("#### Confidence")
        f=performance_by_confidence(service)
        st.dataframe(f,width="stretch",hide_index=True) if not f.empty else st.info("No confidence data yet.")
    with right:
        st.markdown("#### Atlas Score Band")
        f=performance_by_atlas_score(service)
        st.dataframe(f,width="stretch",hide_index=True) if not f.empty else st.info("No Atlas Score data yet.")

    st.divider()
    st.subheader("🧠 Post-Trade Review")
    options={f"{r.ticker} | {r.exit_date} | ${r.realised_pnl:,.2f}":int(r.trade_id) for r in trades.itertuples(index=False)}
    label=st.selectbox("Completed trade",list(options),key="pj_review_trade")
    trade_id=options[label]
    repo=PaperTradeReviewRepository(db_path)
    existing=repo.get_review(trade_id) or {}
    saved_follow=existing.get("followed_plan")
    followed=st.selectbox(
        "Did you follow your plan?",[None,True,False],
        index=[None,True,False].index(None if saved_follow is None else bool(saved_follow)),
        format_func=lambda x:"Not reviewed" if x is None else "Yes" if x else "No",
        key="pj_followed"
    )
    emotion=st.selectbox("Emotional state",["","Calm","Confident","Patient","FOMO","Anxious","Greedy","Frustrated","Revenge Trading","Other"],key="pj_emotion")
    worked=st.text_area("What worked?",value=existing.get("what_worked",""),key="pj_worked")
    wrong=st.text_area("What went wrong?",value=existing.get("what_went_wrong",""),key="pj_wrong")
    lesson=st.text_area("Lesson learned",value=existing.get("lesson_learned",""),key="pj_lesson")
    if st.button("Save Trade Review",type="primary",width="stretch",key="pj_save"):
        repo.save_review(
            account_id=account.id,trade_id=trade_id,followed_plan=followed,
            what_worked=worked,what_went_wrong=wrong,lesson_learned=lesson,
            emotional_state=emotion
        )
        st.success("Trade review saved.")
        st.rerun()
