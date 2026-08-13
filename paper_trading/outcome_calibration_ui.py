"""Outcome Calibration dashboard."""

from __future__ import annotations
import streamlit as st
from .account import PaperAccountService
from .outcome_calibration import calibration_by_match_score, calibration_summary


def display_outcome_calibration(*,db_path="data/paper_trading.db"):
    st.subheader("🎯 Outcome Calibration")
    st.caption(
        "Measure whether Atlas entry-time Historical Match scores actually "
        "corresponded to better completed paper-trade outcomes."
    )
    service=PaperAccountService(db_path)
    summary=calibration_summary(service)
    if summary.calibrated_trades==0:
        st.info(
            "No completed trades can be linked to saved entry-time intelligence "
            "snapshots yet. Place and complete new paper trades to build calibration data."
        )
        return

    cols=st.columns(4)
    cols[0].metric("Calibrated Trades",summary.calibrated_trades)
    cols[1].metric("Score/Return Correlation",
        "—" if summary.correlation is None else f"{summary.correlation:.2f}")
    cols[2].metric("80+ Match Win Rate",
        "—" if summary.high_score_win_rate is None else f"{summary.high_score_win_rate*100:.1f}%")
    cols[3].metric("<60 Match Win Rate",
        "—" if summary.low_score_win_rate is None else f"{summary.low_score_win_rate*100:.1f}%")

    if summary.score_direction_valid is True:
        st.success("Higher-scored setups are currently winning more often than low-scored setups.")
    elif summary.score_direction_valid is False:
        st.warning("Higher-scored setups are not currently outperforming low-scored setups.")
    else:
        st.info("Atlas needs both high- and low-score completed trades before comparing score direction.")

    frame=calibration_by_match_score(service)
    if not frame.empty:
        st.dataframe(frame,width="stretch",hide_index=True,
            column_config={
                "Win_Rate":st.column_config.NumberColumn("Win Rate",format="%.2f"),
                "Average_Return":st.column_config.NumberColumn("Avg Return %",format="%.2f"),
                "Net_PnL":st.column_config.NumberColumn("Net P&L",format="$%.2f"),
                "Expectancy":st.column_config.NumberColumn(format="$%.2f"),
            })

    st.warning(
        "Calibration is descriptive and sample-dependent. A positive relationship "
        "in paper trading does not guarantee future or live-market performance."
    )
