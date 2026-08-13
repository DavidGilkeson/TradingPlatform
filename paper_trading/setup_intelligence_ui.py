"""Streamlit UI for Atlas multi-factor setup intelligence."""

from __future__ import annotations

import streamlit as st

from .account import PaperAccountService
from .trade_scorecard_ui import display_trade_scorecard
from .setup_intelligence import (
    evidence_qualified_setup_leader,
    setup_performance,
)


DIMENSIONS = [
    "Score Band",
    "Confidence Band",
    "Trend Regime",
    "Volatility Regime",
    "Verdict",
]


def display_setup_intelligence(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    st.subheader("🧩 Setup Intelligence")
    st.caption(
        "Discover which combinations of Atlas score, confidence and market "
        "conditions have produced the strongest paper-trading results."
    )

    selected = st.multiselect(
        "Setup dimensions",
        options=DIMENSIONS,
        default=["Score Band", "Confidence Band", "Trend Regime"],
        key="setup_intelligence_dimensions",
    )

    c1, c2 = st.columns(2)

    with c1:
        minimum_trades = st.number_input(
            "Minimum setup trades",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
            key="setup_min_trades",
        )

    with c2:
        evidence = st.number_input(
            "Setup evidence threshold",
            min_value=3,
            max_value=100,
            value=10,
            step=1,
            key="setup_evidence_threshold",
        )

    if not selected:
        st.info("Choose at least one setup dimension.")
        return

    service = PaperAccountService(db_path)

    frame = setup_performance(
        service,
        db_path=db_path,
        dimensions=tuple(selected),
        minimum_trades=int(minimum_trades),
        minimum_evidence_trades=int(evidence),
    )

    if frame.empty:
        st.info(
            "No completed paper-trade setups match the current filters yet."
        )
        return

    leader = evidence_qualified_setup_leader(frame)

    if leader is None:
        st.warning(
            "Atlas can see setup combinations, but none yet have enough "
            "trades to become an evidence-qualified setup."
        )
    else:
        st.success(
            f"Evidence-qualified setup leader: {leader.setup} · "
            f"{leader.trades} trades · "
            f"{leader.win_rate * 100:.1f}% win rate · "
            f"${leader.expectancy:,.2f} expectancy/trade."
        )

        metrics = st.columns(4)
        metrics[0].metric("Leader Trades", leader.trades)
        metrics[1].metric("Win Rate", f"{leader.win_rate * 100:.1f}%")
        metrics[2].metric("Net P&L", f"${leader.net_pnl:,.2f}")
        metrics[3].metric("Reliability", f"{leader.reliability}/100")

    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "Win_Rate": st.column_config.NumberColumn(
                "Win Rate",
                format="%.2f",
            ),
            "Average_Return": st.column_config.NumberColumn(
                "Avg Return %",
                format="%.2f",
            ),
            "Net_PnL": st.column_config.NumberColumn(
                "Net P&L",
                format="$%.2f",
            ),
            "Expectancy": st.column_config.NumberColumn(
                format="$%.2f",
            ),
            "Reliability": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
            ),
            "Insight Ready": st.column_config.CheckboxColumn(),
        },
    )

    st.warning(
        "Multi-factor analysis can overfit quickly. More dimensions create "
        "smaller groups, so Atlas requires evidence thresholds before "
        "promoting a setup."
    )


    st.divider()
    st.markdown("### 🔎 Proposed Trade Scorecard")
    st.caption(
        "Enter a proposed setup to compare it with similar completed "
        "paper trades."
    )

    score_col, confidence_col = st.columns(2)
    with score_col:
        proposed_score = st.number_input(
            "Proposed Atlas Score",
            min_value=0.0,
            max_value=100.0,
            value=80.0,
            step=1.0,
            key="scorecard_atlas_score",
        )
    with confidence_col:
        proposed_confidence = st.number_input(
            "Proposed Confidence",
            min_value=0.0,
            max_value=10.0,
            value=7.0,
            step=1.0,
            key="scorecard_confidence",
        )

    regime_col, volatility_col = st.columns(2)
    with regime_col:
        proposed_trend = st.selectbox(
            "Trend Regime",
            ["", "Bullish", "Bearish", "Sideways", "Mixed"],
            key="scorecard_trend",
        )
    with volatility_col:
        proposed_volatility = st.selectbox(
            "Volatility Regime",
            ["", "Lower Volatility", "High Volatility"],
            key="scorecard_volatility",
        )

    proposed_verdict = st.text_input(
        "Verdict / Trade Reason (optional)",
        key="scorecard_verdict",
    )

    display_trade_scorecard(
        db_path=db_path,
        atlas_score=proposed_score,
        confidence=proposed_confidence,
        trend_regime=proposed_trend or None,
        volatility_regime=proposed_volatility or None,
        verdict=proposed_verdict or None,
        minimum_evidence_trades=int(evidence),
    )
