"""Data models used by the Atlas universal backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(slots=True)
class BacktestConfig:
    """Configuration controlling a single-asset backtest."""

    ticker: str = "UNKNOWN"
    initial_capital: float = 10_000.0
    position_size_pct: float = 1.0
    commission: float = 0.0
    slippage_pct: float = 0.0
    risk_free_rate: float = 0.0
    annual_periods: int = 252
    close_open_position: bool = True

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be greater than zero.")
        if not 0 < self.position_size_pct <= 1:
            raise ValueError("position_size_pct must be between 0 and 1.")
        if self.commission < 0:
            raise ValueError("commission cannot be negative.")
        if self.slippage_pct < 0:
            raise ValueError("slippage_pct cannot be negative.")
        if self.annual_periods <= 0:
            raise ValueError("annual_periods must be positive.")


@dataclass(slots=True)
class Trade:
    """A completed long trade."""

    ticker: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: float
    entry_commission: float
    exit_commission: float
    pnl: float
    return_pct: float
    bars_held: int
    exit_reason: str = "SELL"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0

    @property
    def total_commission(self) -> float:
        return self.entry_commission + self.exit_commission

    def as_dict(self) -> dict[str, Any]:
        """Return a serialisable trade representation."""

        return {
            "ticker": self.ticker,
            "entry_date": self.entry_date,
            "exit_date": self.exit_date,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "shares": self.shares,
            "entry_commission": self.entry_commission,
            "exit_commission": self.exit_commission,
            "total_commission": self.total_commission,
            "pnl": self.pnl,
            "return_pct": self.return_pct,
            "bars_held": self.bars_held,
            "exit_reason": self.exit_reason,
            **self.metadata,
        }


@dataclass(slots=True)
class OpenPosition:
    """Internal representation of an open position."""

    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    entry_commission: float
    entry_bar: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cost_basis(self) -> float:
        return (self.entry_price * self.shares) + self.entry_commission


@dataclass(slots=True)
class BacktestResult:
    """Complete output from one Atlas backtest."""

    strategy_name: str
    ticker: str
    config: BacktestConfig
    trades: list[Trade]
    equity_curve: pd.DataFrame
    metrics: dict[str, float | int | None]
    signals: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    def trades_frame(self) -> pd.DataFrame:
        """Return completed trades as a DataFrame."""

        if not self.trades:
            return pd.DataFrame(
                columns=[
                    "ticker",
                    "entry_date",
                    "exit_date",
                    "entry_price",
                    "exit_price",
                    "shares",
                    "pnl",
                    "return_pct",
                    "bars_held",
                    "exit_reason",
                ]
            )

        return pd.DataFrame([trade.as_dict() for trade in self.trades])

    def summary(self) -> dict[str, Any]:
        """Return a compact result summary."""

        return {
            "strategy": self.strategy_name,
            "ticker": self.ticker,
            **self.metrics,
        }
