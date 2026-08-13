"""Reusable Atlas historical setup scorecard UI."""

from __future__ import annotations

import streamlit as st

from .account import PaperAccountService
from .trade_scorecard import historical_setup_scorecard


def display_trade_scorecard(
    *,
    db_path: str = "data/paper_trading.db",
    atlas_score: float | None = None,
    confidence: float | None = None,
    trend_regime: str | None = None,
    volatility_regime: str | None = None,
    verdict: str | None = None,
    minimum_evidence_trades: int = 10,
) -> None:
    """Render historical evidence for the proposed trade setup."""

    st.markdown("#### 🧠 Historical Setup Scorecard")

    supplied = any(
        value is not None and value != ""
        for value in (
            atlas_score,
            confidence,
            trend_regime,
            volatility_regime,
            verdict,
        )
    )

    if not supplied:
        st.info(
            "Add Atlas Score, confidence or market-regime information to "
            "compare this trade with historical paper trades."
        )
        return

    service = PaperAccountService(db_path)

    card = historical_setup_scorecard(
        service,
        db_path=db_path,
        atlas_score=atlas_score,
        confidence=confidence,
        trend_regime=trend_regime,
        volatility_regime=volatility_regime,
        verdict=verdict,
        minimum_evidence_trades=minimum_evidence_trades,
    )

    cols = st.columns(4)
    cols[0].metric("Historical Match", f"{card.match_score}/100")
    cols[1].metric("Similar Trades", card.matched_trades)
    cols[2].metric(
        "Win Rate",
        "—" if card.win_rate is None else f"{card.win_rate * 100:.1f}%",
    )
    cols[3].metric(
        "Expectancy",
        "—" if card.expectancy is None else f"${card.expectancy:,.2f}",
    )

    if card.verdict == "Historically favourable":
        st.success(f"🟢 {card.verdict}")
    elif card.verdict in {"Historically positive", "Early evidence"}:
        st.info(f"🔵 {card.verdict}")
    elif card.verdict in {
        "Historically negative",
        "Historically unfavourable",
    }:
        st.error(f"🔴 {card.verdict}")
    else:
        st.warning(f"🟠 {card.verdict}")

    st.caption(
        f"Evidence: {card.evidence_level} · "
        f"Sample: {card.sample_grade} · "
        f"Reliability: {card.reliability}/100 · "
        f"Matched on: {', '.join(card.matched_dimensions)}"
    )

    if not card.insight_ready and card.matched_trades > 0:
        st.warning(
            "This setup has historical matches, but not enough completed "
            "paper trades to meet the evidence threshold."
        )

    st.caption(
        "The scorecard describes your paper-trading history. It is not a "
        "prediction, guarantee, or live-trading recommendation."
    )
