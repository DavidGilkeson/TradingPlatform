"""Smart watchlist and one-click paper-trade UI."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .one_click import best_reason_from_row, queue_paper_trade
from .watchlist_intelligence import build_watchlist_intelligence


def display_smart_watchlist(
    *,
    watchlist: list[str],
    market_df: pd.DataFrame | None,
) -> None:
    """Display a ranked watchlist with quick paper-trade queueing."""

    st.subheader("⭐ Smart Watchlist")

    frame = build_watchlist_intelligence(
        watchlist,
        market_df,
    )

    if frame.empty:
        st.info("Your watchlist is empty.")
        return

    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Quick Paper Trade")

    ticker = st.selectbox(
        "Watchlist ticker",
        options=frame["Ticker"].astype(str).tolist(),
        key="smart_watchlist_trade_ticker",
    )

    row = frame.loc[
        frame["Ticker"].astype(str) == ticker
    ].iloc[0]

    reason = best_reason_from_row(row)

    if st.button(
        f"Queue {ticker} Paper Buy",
        type="primary",
        width="stretch",
        key="queue_watchlist_paper_trade",
    ):
        queue_paper_trade(
            ticker=ticker,
            side="BUY",
            reason=reason,
            notes="Queued from Smart Watchlist",
            shares=1.0,
        )

        st.success(
            f"{ticker} queued. Open the Paper Trading tab "
            "to review and confirm the simulated order."
        )
