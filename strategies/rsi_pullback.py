"""RSI pullback strategy."""

from __future__ import annotations

import pandas as pd

from .base_strategy import BaseStrategy


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Wilder-style RSI."""

    change = close.diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    average_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()
    average_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    relative_strength = average_gain / average_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + relative_strength))

    return rsi.fillna(50.0)


class RSIPullbackStrategy(BaseStrategy):
    """Buy RSI recoveries from oversold and sell overbought reversals."""

    name = "RSI Pullback"
    description = "Looks for momentum recovery after oversold conditions."

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        if period <= 1:
            raise ValueError("RSI period must be greater than one.")
        if not 0 < oversold < overbought < 100:
            raise ValueError("RSI thresholds must satisfy 0 < oversold < overbought < 100.")

        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        result = data.copy()
        result["RSI"] = calculate_rsi(result["Close"], self.period)

        previous_rsi = result["RSI"].shift(1)

        recovered_from_oversold = (
            (previous_rsi <= self.oversold)
            & (result["RSI"] > self.oversold)
        )
        fell_from_overbought = (
            (previous_rsi >= self.overbought)
            & (result["RSI"] < self.overbought)
        )

        result["Signal"] = "HOLD"
        result.loc[recovered_from_oversold, "Signal"] = "BUY"
        result.loc[fell_from_overbought, "Signal"] = "SELL"

        return result
