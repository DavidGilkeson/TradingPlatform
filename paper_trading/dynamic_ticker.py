from __future__ import annotations
import pandas as pd


def scan_tickers(market_df: pd.DataFrame | None) -> list[str]:
    """Return unique scan tickers while preserving current scan order."""
    if (
        market_df is None
        or market_df.empty
        or "Ticker" not in market_df.columns
    ):
        return []

    tickers = (
        market_df["Ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
    )

    return list(dict.fromkeys(ticker for ticker in tickers if ticker))


def valid_scan_price(
    ticker: str,
    market_df: pd.DataFrame | None,
) -> float | None:
    """Return a valid current scan price without any artificial fallback."""
    if (
        market_df is None
        or market_df.empty
        or "Ticker" not in market_df.columns
    ):
        return None

    rows = market_df.loc[
        market_df["Ticker"].astype(str).str.upper().str.strip()
        == str(ticker).upper().strip()
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]

    for column in ("Close", "Current Price", "Price", "Latest Price"):
        if column not in row.index:
            continue

        try:
            value = float(row[column])
        except (TypeError, ValueError):
            continue

        if pd.notna(value) and value > 0:
            return value

    return None
