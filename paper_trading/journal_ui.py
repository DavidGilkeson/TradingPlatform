import math
import pandas as pd
import streamlit as st
from .account import PaperAccountService
from .journal_analytics import (
    build_trade_journal_frame, calculate_journal_analytics,
    performance_by_atlas_score, performance_by_confidence
)
from .journal_review import PaperTradeReviewRepository
from .workflow import review_completeness
from .plan_outcome import PlanOutcomeRepository
from .adherence_analytics import (
    build_adherence_frame, adherence_summary, execution_bands
)

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
    st.subheader("🎯 Plan Adherence Analytics")
    adherence=build_adherence_frame(db_path,account.id)
    discipline=adherence_summary(adherence)

    discipline_cols=st.columns(4)
    discipline_cols[0].metric(
        "Reviewed Trades",discipline["reviewed_trades"])
    discipline_cols[1].metric(
        "Plan Follow Rate",
        "—" if discipline["plan_follow_rate"] is None
        else f'{discipline["plan_follow_rate"]:.1%}')
    discipline_cols[2].metric(
        "Avg Execution Quality",
        "—" if discipline["average_execution_rating"] is None
        else f'{discipline["average_execution_rating"]:.1f}/10')
    return_edge=(
        None
        if discipline["followed_avg_return"] is None
        or discipline["not_followed_avg_return"] is None
        else discipline["followed_avg_return"]
             - discipline["not_followed_avg_return"]
    )
    discipline_cols[3].metric(
        "Discipline Return Edge",
        "—" if return_edge is None else f"{return_edge:+.2f}%")

    compare_cols=st.columns(2)
    compare_cols[0].metric(
        "Followed Plan — Avg Return",
        "—" if discipline["followed_avg_return"] is None
        else f'{discipline["followed_avg_return"]:+.2f}%',
        f'Net P&L ${discipline["followed_net_pnl"]:+,.2f}')
    compare_cols[1].metric(
        "Broke Plan — Avg Return",
        "—" if discipline["not_followed_avg_return"] is None
        else f'{discipline["not_followed_avg_return"]:+.2f}%',
        f'Net P&L ${discipline["not_followed_net_pnl"]:+,.2f}')

    bands=execution_bands(adherence)
    if bands.empty:
        st.info(
            "Complete post-trade reviews to build execution-discipline analytics.")
    else:
        st.markdown("##### Performance by Execution Quality")
        st.dataframe(bands,width="stretch",hide_index=True)

    st.caption(
        "These statistics are descriptive. Small samples can be misleading; "
        "Atlas does not change trading rules automatically from this data.")

    st.divider()
    st.subheader("🧠 Post-Trade Review")
    options={f"{r.ticker} | {r.exit_date} | ${r.realised_pnl:,.2f}":int(r.trade_id) for r in trades.itertuples(index=False)}
    label=st.selectbox("Completed trade",list(options),key="pj_review_trade")
    trade_id=options[label]
    repo=PaperTradeReviewRepository(db_path)
    existing=repo.get_review(trade_id) or {}

    comparison=PlanOutcomeRepository(db_path).comparison(trade_id)
    if comparison and comparison["metrics"]:
        plan=comparison["plan"]
        metrics=comparison["metrics"]
        st.markdown("##### 📋 Original Plan vs Actual Outcome")
        plan_cols=st.columns(4)
        plan_cols[0].metric("Planned Entry",f'${metrics["planned_entry"]:,.2f}')
        plan_cols[1].metric("Planned Stop",f'${metrics["planned_stop"]:,.2f}')
        plan_cols[2].metric("Planned Target",f'${metrics["planned_target"]:,.2f}')
        plan_cols[3].metric(
            "Planned R:R",
            "—" if metrics["planned_reward_risk"] is None
            else f'{metrics["planned_reward_risk"]:.2f}:1')
        actual_cols=st.columns(4)
        actual_cols[0].metric("Actual Exit",f'${metrics["actual_exit"]:,.2f}')
        actual_cols[1].metric("Actual Return",f'{metrics["actual_return_pct"]:+.2f}%')
        actual_cols[2].metric("Realised P&L",f'${metrics["realised_pnl"]:+,.2f}')
        actual_cols[3].metric("Outcome vs Plan",metrics["outcome"])
        st.markdown("**Original thesis**")
        st.write(plan.get("thesis") or "—")
        st.markdown("**Original invalidation**")
        st.write(plan.get("invalidation") or "—")
        st.caption(
            "This entry-time plan was saved before the outcome was known. "
            "Use it when judging whether you followed the process.")
        if len(comparison["all_entry_plans"])>1:
            st.info(
                f'This trade used {len(comparison["all_entry_plans"])} entry lots. '
                "The largest-weight entry plan is shown as the primary comparison.")
    else:
        st.info(
            "No structured entry plan is linked to this trade. This is expected "
            "for trades opened before Sprint 33.1.")
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
    lesson=st.text_area(
        "Lesson learned",
        value=existing.get("lesson_learned",""),
        key="pj_lesson",
    )
    review_cols=st.columns(2)
    with review_cols[0]:
        execution_rating=st.slider(
            "Execution quality",
            min_value=1,
            max_value=10,
            value=int(existing.get("execution_rating") or 5),
            help="Rate how well you executed the plan, not whether the trade won.",
            key="pj_execution_rating",
        )
    with review_cols[1]:
        next_action=st.text_area(
            "What will you do differently next time?",
            value=existing.get("next_time_action",""),
            key="pj_next_action",
        )

    draft_review={
        "followed_plan":followed,
        "emotional_state":emotion,
        "what_worked":worked,
        "what_went_wrong":wrong,
        "lesson_learned":lesson,
    }
    completeness=review_completeness(draft_review)
    st.progress(
        completeness,
        text=f"Review completeness: {completeness:.0%}",
    )

    if st.button("Save Trade Review",type="primary",width="stretch",key="pj_save"):
        repo.save_review(
            account_id=account.id,trade_id=trade_id,followed_plan=followed,
            what_worked=worked,what_went_wrong=wrong,lesson_learned=lesson,
            emotional_state=emotion,
            execution_rating=execution_rating,
            next_time_action=next_action,
        )
        st.success("Trade review saved.")
        st.rerun()
