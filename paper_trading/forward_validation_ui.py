"""Forward Validation Scorecard UI."""

import streamlit as st
from .account import PaperAccountService
from .forward_testing import ForwardTestOutcomeRepository
from .forward_validation import build_validation_scorecard, horizon_validation


def display_forward_validation(*,db_path="data/paper_trading.db"):
    st.subheader("🏁 Forward Validation Scorecard")
    st.caption(
        "Evidence-aware validation of Atlas decisions. Sample size is weighted "
        "heavily so a handful of successful observations cannot create a high grade."
    )

    service=PaperAccountService(db_path)
    account=service.active_account()
    outcomes=ForwardTestOutcomeRepository(db_path).outcomes(account.id)
    card=build_validation_scorecard(outcomes)

    top=st.columns(4)
    top[0].metric("Validation Score",f"{card.score}/100")
    top[1].metric("Grade",card.grade)
    top[2].metric("Evidence",card.evidence_level)
    top[3].metric("Observations",card.observations)

    st.info(card.verdict)

    metrics=st.columns(4)
    metrics[0].metric(
        "Decision Edge","—" if card.decision_edge is None
        else f"{card.decision_edge:+.2f}%")
    metrics[1].metric(
        "Avg Excess vs SPY","—" if card.avg_excess_return is None
        else f"{card.avg_excess_return:+.2f}%")
    metrics[2].metric(
        "Beat SPY Rate","—" if card.benchmark_beat_rate is None
        else f"{card.benchmark_beat_rate*100:.1f}%")
    metrics[3].metric(
        "Positive Horizons","—" if card.positive_horizon_rate is None
        else f"{card.positive_horizon_rate*100:.1f}%")

    st.markdown("#### Horizon Validation")
    table=horizon_validation(outcomes,minimum_per_group=5)
    if table.empty:
        st.info("No resolved forward outcomes yet.")
    else:
        st.dataframe(table,width="stretch",hide_index=True)

    st.markdown("#### Evidence Safeguards")
    st.write(
        "A horizon becomes **Evidence Ready** only after at least 5 TAKEN and "
        "5 SKIPPED observations. Overall evidence remains **Early** below 20 "
        "observations, **Developing** from 20, **Moderate** from 50, and "
        "**Strong** from 100."
    )
    st.warning(
        "A high validation score is not proof of future profitability. "
        "Forward testing reduces hindsight bias but does not remove market, "
        "execution, regime or overfitting risk."
    )
