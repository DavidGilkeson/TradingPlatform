"""Market-regime classification and paper-trade regime analytics."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(slots=True)
class MarketRegime:
    trend: str
    volatility: str
    label: str


def classify_market_regime(
    *,
    close: float,
    ma_short: float,
    ma_long: float,
    volatility_pct: float | None = None,
    high_volatility_threshold: float = 2.0,
    trend_buffer_pct: float = 0.5,
) -> MarketRegime:
    """Classify a market snapshot into trend and volatility regimes."""

    close = float(close)
    ma_short = float(ma_short)
    ma_long = float(ma_long)

    if close <= 0 or ma_short <= 0 or ma_long <= 0:
        raise ValueError("Close and moving averages must be greater than zero.")

    separation_pct = abs(ma_short - ma_long) / ma_long * 100

    if separation_pct < float(trend_buffer_pct):
        trend = "Sideways"
    elif ma_short > ma_long and close >= ma_short:
        trend = "Bullish"
    elif ma_short < ma_long and close <= ma_short:
        trend = "Bearish"
    else:
        trend = "Mixed"

    if volatility_pct is None:
        volatility = "Unknown Volatility"
    elif float(volatility_pct) >= float(high_volatility_threshold):
        volatility = "High Volatility"
    else:
        volatility = "Lower Volatility"

    return MarketRegime(
        trend=trend,
        volatility=volatility,
        label=f"{trend} · {volatility}",
    )


def regime_performance(
    trades: pd.DataFrame,
    *,
    minimum_trades: int = 1,
) -> pd.DataFrame:
    """Aggregate completed trades by saved market-regime label."""

    if trades is None or trades.empty or "market_regime" not in trades.columns:
        return pd.DataFrame()

    working = trades.copy()
    working = working.dropna(subset=["market_regime"])
    working["market_regime"] = (
        working["market_regime"].astype(str).str.strip()
    )
    working = working[working["market_regime"] != ""]

    if working.empty:
        return pd.DataFrame()

    for column in ("realised_pnl", "return_pct"):
        working[column] = pd.to_numeric(
            working[column],
            errors="coerce",
        )

    grouped = (
        working.groupby("market_regime", as_index=False)
        .agg(
            Trades=("trade_id", "count"),
            Win_Rate=("realised_pnl", lambda s: float((s > 0).mean())),
            Average_Return=("return_pct", "mean"),
            Net_PnL=("realised_pnl", "sum"),
            Expectancy=("realised_pnl", "mean"),
        )
    )

    return (
        grouped[grouped["Trades"] >= int(minimum_trades)]
        .sort_values(
            ["Expectancy", "Trades"],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )
