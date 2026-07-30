"""Integration layer between Atlas strategies and the backtesting engine."""

from __future__ import annotations

import pandas as pd

from .models import BacktestConfig, BacktestResult
from .simulator import run_backtest


def backtest_strategy(
    strategy: object,
    market_data: pd.DataFrame,
    *,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Run any Atlas BaseStrategy-compatible object through the backtester."""

    if not hasattr(strategy, "run"):
        raise TypeError("strategy must provide a run(data) method.")

    strategy_result = strategy.run(market_data)

    if not hasattr(strategy_result, "signals"):
        raise TypeError("Strategy result must expose a signals DataFrame.")

    strategy_name = getattr(
        strategy_result,
        "strategy_name",
        getattr(strategy, "name", strategy.__class__.__name__),
    )

    metadata = getattr(strategy_result, "metadata", {}) or {}

    return run_backtest(
        strategy_result.signals,
        strategy_name=strategy_name,
        config=config,
        metadata=metadata,
    )
