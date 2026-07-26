"""Core interfaces and result models for Atlas trading strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


REQUIRED_PRICE_COLUMNS = {"Close"}


@dataclass(slots=True)
class StrategyResult:
    """Standard result returned by every Atlas strategy."""

    strategy_name: str
    signals: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def buy_count(self) -> int:
        return int((self.signals["Signal"] == "BUY").sum())

    @property
    def sell_count(self) -> int:
        return int((self.signals["Signal"] == "SELL").sum())

    @property
    def hold_count(self) -> int:
        return int((self.signals["Signal"] == "HOLD").sum())

    def summary(self) -> dict[str, Any]:
        """Return a compact, serialisable summary."""

        return {
            "strategy": self.strategy_name,
            "rows": len(self.signals),
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "hold_count": self.hold_count,
            "metadata": self.metadata,
        }


class BaseStrategy(ABC):
    """Abstract base class implemented by every Atlas strategy."""

    name = "Unnamed Strategy"
    description = ""
    version = "1.0"
    required_columns: set[str] = set(REQUIRED_PRICE_COLUMNS)

    def validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalise price data without mutating the caller."""

        if not isinstance(data, pd.DataFrame):
            raise TypeError("Strategy data must be a pandas DataFrame.")

        if data.empty:
            raise ValueError("Strategy data cannot be empty.")

        missing = self.required_columns.difference(data.columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing required columns: {missing_text}")

        clean = data.copy()

        for column in self.required_columns:
            clean[column] = pd.to_numeric(clean[column], errors="coerce")

        clean = clean.dropna(subset=list(self.required_columns))

        if clean.empty:
            raise ValueError("No usable rows remain after cleaning strategy data.")

        return clean.sort_index()

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame containing a Signal column."""

    def run(self, data: pd.DataFrame) -> StrategyResult:
        """Validate input, generate signals, and return a standard result."""

        clean = self.validate_data(data)
        signals = self.generate_signals(clean)

        if not isinstance(signals, pd.DataFrame):
            raise TypeError("generate_signals() must return a pandas DataFrame.")

        if "Signal" not in signals.columns:
            raise ValueError("Strategy result must contain a Signal column.")

        allowed = {"BUY", "SELL", "HOLD"}
        invalid = set(signals["Signal"].dropna().astype(str).str.upper()) - allowed
        if invalid:
            raise ValueError(
                "Signal column contains unsupported values: "
                + ", ".join(sorted(invalid))
            )

        signals = signals.copy()
        signals["Signal"] = signals["Signal"].fillna("HOLD").astype(str).str.upper()

        return StrategyResult(
            strategy_name=self.name,
            signals=signals,
            metadata={
                "description": self.description,
                "version": self.version,
            },
        )
