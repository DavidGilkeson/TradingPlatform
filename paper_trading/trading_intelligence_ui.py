"""Evidence-aware Streamlit UI for Atlas paper-trading intelligence."""

from __future__ import annotations

import streamlit as st

from .account import PaperAccountService
from .pattern_confidence import add_sample_quality, strongest_eligible_pattern
from .trading_intelligence import (
    derive_intelligence_summary,
    performance_by_atlas_score,
    performance_by_confidence,
    performance_by_ticker,
    performance_by_verdict,
)


def _show_table(frame, *, minimum_evidence_trades: int) -> None:
    if frame.empty:
        st.info("No pattern meets the selected trade-count filter.")
        return

    quality = add_sample_quality(
        frame,
        minimum_evidence_trades=minimum_evidence_trades,
    )

    st.dataframe(
        quality,
        width="stretch",
        hide_index=True,
        column_config={
            "Win_Rate": st.column_config.NumberColumn(format="%.1f%%"),
            "Average_Return": st.column_config.NumberColumn(format="%.2f%%"),
            "Net_PnL": st.column_config.NumberColumn(format="$%.2f"),
            "Expectancy": st.column_config.NumberColumn(format="$%.2f"),
            "Reliability": st.column_config.ProgressColumn(
                "Reliability",
                min_value=0,
                max_value=100,
                format="%d",
            ),
            "Insight Ready": st.column_config.CheckboxColumn(
                "Insight Ready"
            ),
        },
    )


def display_trading_intelligence(*, db_path="data/paper_trading.db"):
    service = PaperAccountService(db_path)

    st.subheader("🧠 Atlas Trading Intelligence")
    st.caption(
        "Analyse completed paper trades while accounting for how much evidence "
        "actually supports each apparent pattern."
    )

    filter_col, evidence_col = st.columns(2)

    with filter_col:
        minimum_trades = st.number_input(
            "Show patterns with at least",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
            key="intelligence_minimum_trades",
        )

    with evidence_col:
        minimum_evidence = st.number_input(
            "Trades required before Atlas trusts a pattern",
            min_value=3,
            max_value=100,
            value=10,
            step=1,
            key="intelligence_minimum_evidence",
        )

    summary = derive_intelligence_summary(
        service,
        minimum_trades=int(minimum_trades),
    )

    if summary.total_trades == 0:
        st.info(
            "Atlas needs completed paper trades before it can identify "
            "performance patterns."
        )
        return

    ticker = performance_by_ticker(service, int(minimum_trades))
    score = performance_by_atlas_score(service, int(minimum_trades))
    confidence = performance_by_confidence(service, int(minimum_trades))
    verdict = performance_by_verdict(service, int(minimum_trades))

    strongest = strongest_eligible_pattern(
        [
            ("ticker", ticker),
            ("Atlas Score Band", score),
            ("confidence", confidence),
            ("Verdict", verdict),
        ],
        minimum_evidence_trades=int(minimum_evidence),
    )

    metrics = st.columns(4)
    metrics[0].metric("Completed Trades", summary.total_trades)
    metrics[1].metric(
        "Evidence Threshold",
        f"{int(minimum_evidence)} trades",
    )
    metrics[2].metric(
        "Best Raw Score Band",
        summary.best_atlas_score_band or "—",
    )
    metrics[3].metric(
        "Best Raw Ticker",
        summary.best_ticker or "—",
    )

    if strongest is None:
        st.warning(
            "Atlas sees early patterns, but none currently have enough trades "
            "to pass the evidence threshold. Keep paper trading."
        )
    else:
        label, expectancy, trades = strongest
        st.success(
            f"Evidence-qualified leader: {label} · "
            f"{trades} trades · ${expectancy:,.2f} expectancy per trade."
        )

    st.warning(
        "A high win rate or expectancy from a small sample can be misleading. "
        "Atlas now labels sample quality instead of treating every pattern as "
        "equally trustworthy."
    )

    tabs = st.tabs(
        ["By Ticker", "By Atlas Score", "By Confidence", "By Verdict/Reason"]
    )

    for tab, frame in zip(tabs, [ticker, score, confidence, verdict]):
        with tab:
            _show_table(
                frame,
                minimum_evidence_trades=int(minimum_evidence),
            )

    with st.expander("How Atlas judges pattern confidence"):
        st.markdown(
            """
- **Very Small:** fewer than 5 trades
- **Small:** 5–9 trades
- **Developing:** 10–19 trades
- **Useful:** 20–49 trades
- **Strong:** 50+ trades

The reliability score is based on **sample size only**. It does not mean a
strategy has a guaranteed probability of success.
            """
        )
