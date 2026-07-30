"""Equity-curve and drawdown helpers."""

from __future__ import annotations

import pandas as pd


def calculate_drawdown(equity: pd.Series) -> pd.DataFrame:
    """Calculate running peak, drawdown amount, and drawdown percentage."""

    if equity.empty:
        return pd.DataFrame(
            columns=["Equity", "Peak", "Drawdown", "Drawdown Pct"]
        )

    clean = pd.to_numeric(equity, errors="coerce").ffill().dropna()

    if clean.empty:
        return pd.DataFrame(
            columns=["Equity", "Peak", "Drawdown", "Drawdown Pct"]
        )

    peak = clean.cummax()
    drawdown = clean - peak
    drawdown_pct = clean / peak - 1.0

    return pd.DataFrame(
        {
            "Equity": clean,
            "Peak": peak,
            "Drawdown": drawdown,
            "Drawdown Pct": drawdown_pct,
        }
    )


def daily_returns(equity_curve: pd.DataFrame) -> pd.Series:
    """Extract periodic equity returns from a backtest curve."""

    if equity_curve.empty or "Equity" not in equity_curve.columns:
        return pd.Series(dtype="float64")

    return (
        pd.to_numeric(equity_curve["Equity"], errors="coerce")
        .pct_change()
        .replace([float("inf"), float("-inf")], pd.NA)
        .dropna()
    )
