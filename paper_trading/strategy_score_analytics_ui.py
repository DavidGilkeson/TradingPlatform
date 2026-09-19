from __future__ import annotations
import streamlit as st
from .account import PaperAccountService
from .pattern_confidence import add_sample_quality, strongest_eligible_pattern
from .strategy_score_analytics import (
    performance_by_entry_atlas_score,performance_by_entry_confidence,
    performance_by_entry_verdict,score_monotonicity,
)

def _table(f, threshold):
    if f.empty:
        st.info("No completed trades with captured entry-time intelligence yet.")
        return
    st.dataframe(add_sample_quality(f,minimum_evidence_trades=threshold),width="stretch",hide_index=True,
        column_config={"Win_Rate":st.column_config.NumberColumn(format="%.1f%%"),
        "Average_Return":st.column_config.NumberColumn(format="%.2f%%"),
        "Net_PnL":st.column_config.NumberColumn(format="$%.2f"),
        "Expectancy":st.column_config.NumberColumn(format="$%.2f")})

def display_strategy_score_analytics(*,db_path="data/paper_trading.db"):
    service=PaperAccountService(db_path); account=service.active_account()
    st.subheader("🎯 Strategy & Atlas Score Analytics")
    st.caption("Tests whether intelligence captured when you entered a paper trade is associated with later outcomes. Results are descriptive evidence, not predictions.")
    c1,c2=st.columns(2)
    minimum=int(c1.number_input("Show groups with at least",1,100,1,1,key="score_analytics_min"))
    evidence=int(c2.number_input("Evidence threshold",3,100,10,1,key="score_analytics_evidence"))
    score=performance_by_entry_atlas_score(db_path,account.id,minimum)
    confidence=performance_by_entry_confidence(db_path,account.id,minimum)
    verdict=performance_by_entry_verdict(db_path,account.id,minimum)
    relation=score_monotonicity(score)
    leader=strongest_eligible_pattern([("Atlas Score Band",score),("confidence",confidence),("Entry Verdict",verdict)],minimum_evidence_trades=evidence)
    m=st.columns(3)
    m[0].metric("Score Relationship",relation or "Insufficient evidence")
    m[1].metric("Evidence Threshold",f"{evidence} trades")
    m[2].metric("Evidence-Qualified Leader",leader[0] if leader else "None yet")
    if leader:
        st.success(f"Observed evidence-qualified pattern: {leader[0]} · {leader[2]} trades · ${leader[1]:,.2f} expectancy per trade.")
    else:
        st.warning("No group currently clears the evidence threshold. Keep paper trading before drawing conclusions.")
    tabs=st.tabs(["Atlas Score","Confidence","Entry Verdict"])
    for tab,frame in zip(tabs,[score,confidence,verdict]):
        with tab:_table(frame,evidence)
    st.caption("Scaled entries use exact BUY-order lineage and allocated P&L, so one completed trade is not accidentally counted as multiple full-P&L outcomes.")
