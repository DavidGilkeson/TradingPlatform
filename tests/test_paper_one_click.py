"""Tests for Sprint 29.6 Smart Watchlist helpers."""

from __future__ import annotations

import pandas as pd

from paper_trading.one_click import best_reason_from_row
from paper_trading.watchlist_intelligence import build_watchlist_intelligence


def test_watchlist_enriches_and_ranks() -> None:
    market = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Atlas Score": 91,
                "Atlas Verdict": "Strong Buy",
                "Signal": "BUY",
                "RSI": 55,
            },
            {
                "Ticker": "MSFT",
                "Atlas Score": 80,
                "Atlas Verdict": "Buy",
                "Signal": "BUY",
                "RSI": 60,
            },
        ]
    )

    result = build_watchlist_intelligence(
        ["MSFT", "AAPL"],
        market,
    )

    assert list(result["Ticker"]) == ["AAPL", "MSFT"]
    assert result.iloc[0]["Atlas Score"] == 91


def test_watchlist_handles_no_market_data() -> None:
    result = build_watchlist_intelligence(
        ["NVDA"],
        None,
    )

    assert list(result["Ticker"]) == ["NVDA"]


def test_watchlist_removes_duplicates() -> None:
    result = build_watchlist_intelligence(
        ["AAPL", "AAPL", "MSFT"],
        None,
    )

    assert list(result["Ticker"]) == ["AAPL", "MSFT"]


def test_best_reason_uses_verdict_and_score() -> None:
    reason = best_reason_from_row(
        {
            "Atlas Verdict": "Strong Buy",
            "Atlas Score": 94,
        }
    )

    assert reason == "Strong Buy · Atlas Score 94.0"
