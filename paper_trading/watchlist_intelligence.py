"""Smart watchlist helpers for Atlas paper trading."""

from __future__ import annotations

import pandas as pd


def build_watchlist_intelligence(
    watchlist: list[str],
    market_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Return watchlist rows enriched with current scanner data."""

    if not watchlist:
        return pd.DataFrame(
            columns=[
                "Ticker",
                "Atlas Score",
                "Atlas Grade",
                "Atlas Verdict",
                "Atlas Confidence",
                "Signal",
                "RSI",
                "Relative Volume",
                "Strength (%)",
                "Close",
            ]
        )

    base = pd.DataFrame(
        {
            "Ticker": [
                str(ticker).upper().strip()
                for ticker in watchlist
                if str(ticker).strip()
            ]
        }
    ).drop_duplicates()

    if market_df is None or market_df.empty or "Ticker" not in market_df.columns:
        return base.reset_index(drop=True)

    market = market_df.copy()
    market["Ticker"] = market["Ticker"].astype(str).str.upper()

    wanted = [
        column
        for column in [
            "Ticker",
            "Atlas Score",
            "Atlas Grade",
            "Atlas Verdict",
            "Atlas Confidence",
            "Atlas Stars",
            "Signal",
            "RSI",
            "Relative Volume",
            "Strength (%)",
            "Close",
        ]
        if column in market.columns
    ]

    merged = base.merge(
        market[wanted],
        on="Ticker",
        how="left",
    )

    if "Atlas Score" in merged.columns:
        merged["Atlas Score"] = pd.to_numeric(
            merged["Atlas Score"],
            errors="coerce",
        )
        merged = merged.sort_values(
            by="Atlas Score",
            ascending=False,
            na_position="last",
        )

    return merged.reset_index(drop=True)
