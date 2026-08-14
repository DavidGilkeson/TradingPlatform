"""Cohort Validation UI."""

import streamlit as st
from .account import PaperAccountService
from .forward_testing import ForwardTestOutcomeRepository
from .cohort_validation import (
    score_band_validation,
    confidence_validation,
    decision_cohort_validation,
    strongest_cohort,
    score_monotonicity,
)


def _show_table(table):
    if table.empty:
        st.info("No resolved observations are available for this cohort yet.")
        return
    st.dataframe(
        table,width="stretch",hide_index=True,
        column_config={
            "Average Return":st.column_config.NumberColumn(format="%.2f%%"),
            "Positive Rate":st.column_config.NumberColumn(format="%.2f"),
            "Avg Excess Return":st.column_config.NumberColumn(format="%.2f%%"),
            "Beat Benchmark Rate":st.column_config.NumberColumn(format="%.2f"),
            "Decision Edge":st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


def display_cohort_validation(*,db_path="data/paper_trading.db"):
    st.subheader("🔬 Cohort Validation")
    st.caption(
        "Break forward-test evidence into groups to discover where Atlas's "
        "observed edge is actually coming from."
    )

    service=PaperAccountService(db_path)
    account=service.active_account()
    outcomes=ForwardTestOutcomeRepository(db_path).outcomes(account.id)

    if outcomes.empty:
        st.info("Resolve forward-test outcomes to begin cohort validation.")
        return

    score_table=score_band_validation(outcomes)
    confidence_table=confidence_validation(outcomes)
    decision_table=decision_cohort_validation(outcomes)

    leader=strongest_cohort(score_table,"Score Band")
    if leader is None:
        st.info(
            "No score cohort has enough benchmark-linked observations to "
            "declare an evidence-qualified leader yet."
        )
    else:
        cols=st.columns(4)
        cols[0].metric("Strongest Score Band",leader["cohort"])
        cols[1].metric("Horizon",f'{leader["horizon_days"]} days')
        cols[2].metric("Observations",leader["observations"])
        cols[3].metric(
            "Avg Excess vs SPY",f'{leader["avg_excess_return"]:+.2f}%')

    st.markdown("#### Atlas Score Bands")
    _show_table(score_table)

    available=sorted(
        int(v) for v in outcomes["horizon_days"].dropna().unique())
    if available:
        horizon=st.selectbox(
            "Score/return correlation horizon",
            available,
            format_func=lambda x:f"{x} trading day(s)",
            key="cohort_score_horizon",
        )
        correlation=score_monotonicity(outcomes,horizon)
        if correlation is None:
            st.info("Not enough varied score observations for correlation yet.")
        else:
            st.metric("Atlas Score ↔ Realised Return",f"{correlation:.2f}")
            if correlation>0.25:
                st.success("Higher Atlas Scores are currently associated with higher returns.")
            elif correlation<-0.25:
                st.warning("Higher Atlas Scores are currently associated with lower returns.")
            else:
                st.info("The current score/return relationship is weak.")

    st.markdown("#### Confidence Bands")
    _show_table(confidence_table)

    st.markdown("#### Decision Cohorts")
    _show_table(decision_table)

    st.warning(
        "Cohort results remain descriptive evidence, not proof of causation. "
        "Small groups can be noisy; Evidence Ready requires at least five "
        "resolved observations in that cohort/horizon."
    )
