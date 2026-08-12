"""Market Regime Intelligence UI."""

from __future__ import annotations

import streamlit as st

from .account import PaperAccountService
from .regime_intelligence import market_regime_intelligence


def display_regime_intelligence(
    *,
    db_path: str = "data/paper_trading.db",
) -> None:
    st.subheader("🌦️ Market Regime Intelligence")
    st.caption(
        "Compare completed paper trades by the market environment saved at "
        "trade entry."
    )

    c1, c2 = st.columns(2)
    with c1:
        minimum_trades = st.number_input(
            "Minimum regime trades",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
            key="regime_min_trades",
        )
    with c2:
        evidence = st.number_input(
            "Regime evidence threshold",
            min_value=3,
            max_value=100,
            value=10,
            step=1,
            key="regime_evidence_threshold",
        )

    service = PaperAccountService(db_path)
    frame = market_regime_intelligence(
        service,
        db_path=db_path,
        minimum_trades=int(minimum_trades),
        minimum_evidence_trades=int(evidence),
    )

    if frame.empty:
        st.info(
            "No completed paper trades have saved market-regime metadata yet. "
            "New regime-tagged trades will populate this analysis."
        )
        return

    ready = frame[frame["Insight Ready"]]

    if ready.empty:
        st.warning(
            "Regime results exist, but none yet meet the selected evidence "
            "threshold."
        )
    else:
        leader = ready.sort_values(
            ["Expectancy", "Trades"],
            ascending=[False, False],
        ).iloc[0]
        st.success(
            f"Evidence-qualified regime leader: {leader['market_regime']} · "
            f"{int(leader['Trades'])} trades · "
            f"${float(leader['Expectancy']):,.2f} expectancy/trade."
        )

    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "Reliability": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
            ),
            "Insight Ready": st.column_config.CheckboxColumn(),
        },
    )

    st.warning(
        "Regime performance is descriptive paper-trading evidence, not a "
        "forecast. Small samples can still be misleading."
    )
