"""Atlas Intelligence Health dashboard."""

from __future__ import annotations
import streamlit as st
from .account import PaperAccountService
from .intelligence_health import (
    intelligence_health,
    strongest_setup,
    strongest_regime,
    calibration_bands,
)


def display_intelligence_health(*,db_path="data/paper_trading.db"):
    st.subheader("🧠 Intelligence Health")
    st.caption(
        "A consolidated view of how much evidence Atlas has accumulated and "
        "how trustworthy its paper-trading analytics are becoming."
    )

    service=PaperAccountService(db_path)
    health=intelligence_health(service)

    top=st.columns(4)
    top[0].metric("Intelligence Health",f"{health.score}/100")
    top[1].metric("Evidence Grade",health.grade)
    top[2].metric("Completed Trades",health.completed_trades)
    top[3].metric("Calibrated Trades",health.calibrated_trades)

    if health.score>=70:
        st.success(f"🟢 {health.status}")
    elif health.score>=40:
        st.warning(f"🟠 {health.status}")
    else:
        st.info(f"🔵 {health.status}")

    st.markdown("#### Evidence Coverage")
    coverage=st.columns(4)
    coverage[0].metric(
        "Calibration Coverage",f"{health.calibration_coverage*100:.1f}%")
    coverage[1].metric(
        "Exact-Link Coverage",f"{health.exact_link_coverage*100:.1f}%")
    coverage[2].metric("Exact Entry Links",health.exact_links)
    coverage[3].metric("Evidence-Ready Setups",health.evidence_ready_setups)

    if health.legacy_unlinked:
        st.caption(
            f"{health.legacy_unlinked} legacy completed trade(s) predate exact "
            "entry linkage and are not guessed."
        )

    st.markdown("#### Calibration Signal")
    if health.correlation is None:
        st.info("Not enough varied calibrated outcomes yet to calculate a useful correlation.")
    else:
        st.metric("Historical Match ↔ Return Correlation",f"{health.correlation:.2f}")
        if health.correlation>0.25:
            st.success("Higher Historical Match scores currently align positively with returns.")
        elif health.correlation<-0.25:
            st.warning("Historical Match scores currently align negatively with returns.")
        else:
            st.info("The current score/return relationship is weak or inconclusive.")

    leader=strongest_setup(service)
    st.markdown("#### Strongest Evidence-Qualified Setup")
    if leader is None:
        st.info("No setup has reached the evidence threshold yet.")
    else:
        cols=st.columns(4)
        cols[0].metric("Setup",leader.setup)
        cols[1].metric("Trades",leader.trades)
        cols[2].metric("Win Rate",f"{leader.win_rate*100:.1f}%")
        cols[3].metric("Expectancy",f"${leader.expectancy:,.2f}")

    regime=strongest_regime(service)
    st.markdown("#### Strongest Evidence-Qualified Regime")
    if regime is None:
        st.info("No market regime has enough evidence yet.")
    else:
        st.dataframe([regime],width="stretch",hide_index=True)

    bands=calibration_bands(service)
    st.markdown("#### Historical Match Performance")
    if bands.empty:
        st.info("Complete new snapshot-linked paper trades to populate calibration bands.")
    else:
        st.dataframe(bands,width="stretch",hide_index=True)

    st.divider()
    st.caption(
        "Health measures evidence maturity, linkage quality and coverage—not "
        "whether Atlas can predict future returns. Paper results can differ "
        "materially from live trading."
    )
