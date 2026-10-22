"""Ticker universe and safe live-price fallback for the Paper Order Ticket."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from atlas_cache import TTLCache

# A short-lived cache avoids repeated network calls during Streamlit reruns.
_PRICE_CACHE = TTLCache(ttl_seconds=60, max_entries=500)


def load_local_ticker_universe(
    csv_path: str = "data/sp500.csv",
) -> list[str]:
    """Load locally cached S&P 500 symbols without requiring a market scan."""
    path = Path(csv_path)
    if not path.exists():
        return []

    try:
        frame = pd.read_csv(path)
    except Exception:
        return []

    candidates = ("Ticker", "Symbol", "ticker", "symbol")
    column = next((name for name in candidates if name in frame.columns), None)
    if column is None:
        return []

    values = (
        frame[column]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
        .str.replace(".", "-", regex=False)
    )
    return list(dict.fromkeys(value for value in values if value))


def _fetch_latest_live_price(ticker: str) -> float | None:
    """Return a recent market price using yfinance, or None on failure.

    This is a real market-data fallback, never an artificial default price.
    """
    ticker = str(ticker).upper().strip()
    if not ticker:
        return None

    try:
        import yfinance as yf
    except ImportError:
        return None

    try:
        data = yf.download(
            ticker,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=15,
        )
    except Exception:
        return None

    if data is None or data.empty or "Close" not in data:
        return None

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        return None

    value = float(close.iloc[-1])
    return value if value > 0 else None


def build_ticker_options(
    *,
    scan_tickers: list[str] | None = None,
    local_tickers: list[str] | None = None,
    position_tickers: list[str] | None = None,
    intent_ticker: str | None = None,
) -> list[str]:
    """Merge ticker sources while preserving priority and order."""
    merged = []

    if intent_ticker:
        merged.append(str(intent_ticker).upper().strip())

    merged.extend(scan_tickers or [])
    merged.extend(local_tickers or [])
    merged.extend(position_tickers or [])

    return list(
        dict.fromkeys(
            str(value).upper().strip()
            for value in merged
            if str(value).strip()
        )
    )


def latest_live_price(ticker: str) -> float | None:
    """Return a cached recent market price, refreshing at most once per TTL.

    Failed lookups are not cached, so transient network errors can recover on
    the next call. Use clear_price_cache() after an explicit market refresh.
    """
    symbol = str(ticker or "").upper().strip()
    if not symbol:
        return None
    return _PRICE_CACHE.get_or_compute(symbol, lambda: _fetch_latest_live_price(symbol))


def clear_price_cache(ticker: str | None = None) -> None:
    """Invalidate one ticker or the entire live-price cache."""
    _PRICE_CACHE.clear(str(ticker).upper().strip() if ticker else None)
