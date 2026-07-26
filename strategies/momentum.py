"""Price momentum strategy."""

from __future__ import annotations

import pandas as pd

from .base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """Trade when medium-term return crosses momentum thresholds."""

    name = "Momentum"
    description = "Uses rolling price returns to detect strengthening momentum."

    def __init__(
        self,
        lookback: int = 20,
        buy_threshold: float = 0.05,
        sell_threshold: float = -0.05,
    ) -> None:
        if lookback <= 1:
            raise ValueError("Momentum lookback must be greater than one.")
        if sell_threshold >= buy_threshold:
            raise ValueError("sell_threshold must be below buy_threshold.")

        self.lookback = lookback
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        result = data.copy()
        result["Momentum Return"] = result["Close"].pct_change(self.lookback)

        previous = result["Momentum Return"].shift(1)

        entered_buy_zone = (
            (previous <= self.buy_threshold)
            & (result["Momentum Return"] > self.buy_threshold)
        )
        entered_sell_zone = (
            (previous >= self.sell_threshold)
            & (result["Momentum Return"] < self.sell_threshold)
        )

        result["Signal"] = "HOLD"
        result.loc[entered_buy_zone, "Signal"] = "BUY"
        result.loc[entered_sell_zone, "Signal"] = "SELL"

        return result
