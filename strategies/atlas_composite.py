"""Atlas composite strategy combining trend, momentum, RSI, and volume."""

from __future__ import annotations

import pandas as pd

from .base_strategy import BaseStrategy
from .rsi_pullback import calculate_rsi


class AtlasCompositeStrategy(BaseStrategy):
    """Generate signals from a transparent multi-factor score."""

    name = "Atlas Composite"
    description = "Combines trend, RSI, momentum, and relative volume."

    required_columns = {"Close"}

    def __init__(
        self,
        buy_score: int = 3,
        sell_score: int = -2,
    ) -> None:
        if sell_score >= buy_score:
            raise ValueError("sell_score must be lower than buy_score.")

        self.buy_score = buy_score
        self.sell_score = sell_score

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        result = data.copy()

        result["MA20"] = result["Close"].rolling(20).mean()
        result["MA50"] = result["Close"].rolling(50).mean()
        result["RSI"] = calculate_rsi(result["Close"], 14)
        result["Momentum Return"] = result["Close"].pct_change(20)

        if "Volume" in result.columns:
            numeric_volume = pd.to_numeric(result["Volume"], errors="coerce")
            volume_average = numeric_volume.rolling(20).mean()
            result["Relative Volume"] = numeric_volume / volume_average
        else:
            result["Relative Volume"] = 1.0

        score = pd.Series(0, index=result.index, dtype="int64")

        score += (result["Close"] > result["MA20"]).astype(int)
        score += (result["MA20"] > result["MA50"]).astype(int)
        score += result["RSI"].between(40, 65).astype(int)
        score += (result["Momentum Return"] > 0).astype(int)
        score += (result["Relative Volume"] >= 1.2).astype(int)

        score -= (result["Close"] < result["MA50"]).astype(int)
        score -= (result["RSI"] >= 75).astype(int)
        score -= (result["Momentum Return"] < -0.05).astype(int)

        result["Strategy Score"] = score
        result["Signal"] = "HOLD"
        result.loc[result["Strategy Score"] >= self.buy_score, "Signal"] = "BUY"
        result.loc[result["Strategy Score"] <= self.sell_score, "Signal"] = "SELL"

        return result
