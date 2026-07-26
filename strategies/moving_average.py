"""Moving-average crossover strategy."""

from __future__ import annotations

import pandas as pd

from .base_strategy import BaseStrategy


class MovingAverageCrossStrategy(BaseStrategy):
    """Buy when the fast average crosses above the slow average."""

    name = "Moving Average Cross"
    description = "Trades fast and slow moving-average crossovers."

    def __init__(self, fast_window: int = 20, slow_window: int = 50) -> None:
        if fast_window <= 0 or slow_window <= 0:
            raise ValueError("Moving-average windows must be positive.")
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window.")

        self.fast_window = fast_window
        self.slow_window = slow_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        result = data.copy()

        result["Fast MA"] = result["Close"].rolling(self.fast_window).mean()
        result["Slow MA"] = result["Close"].rolling(self.slow_window).mean()

        previous_fast = result["Fast MA"].shift(1)
        previous_slow = result["Slow MA"].shift(1)

        crossed_above = (
            (result["Fast MA"] > result["Slow MA"])
            & (previous_fast <= previous_slow)
        )
        crossed_below = (
            (result["Fast MA"] < result["Slow MA"])
            & (previous_fast >= previous_slow)
        )

        result["Signal"] = "HOLD"
        result.loc[crossed_above, "Signal"] = "BUY"
        result.loc[crossed_below, "Signal"] = "SELL"

        return result
