"""Compare multiple Atlas strategies on the same market data."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .models import BacktestConfig, BacktestResult
from .runner import backtest_strategy


def compare_strategies(
    strategies: Mapping[str, object],
    market_data: pd.DataFrame,
    *,
    config: BacktestConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, BacktestResult]]:
    """Backtest multiple strategies and return a ranked comparison table."""

    results: dict[str, BacktestResult] = {}
    rows: list[dict[str, object]] = []

    for key, strategy in strategies.items():
        result = backtest_strategy(
            strategy,
            market_data,
            config=config,
        )
        results[key] = result

        rows.append(
            {
                "Strategy Key": key,
                "Strategy": result.strategy_name,
                "Total Return": result.metrics["total_return"],
                "CAGR": result.metrics["cagr"],
                "Sharpe Ratio": result.metrics["sharpe_ratio"],
                "Sortino Ratio": result.metrics["sortino_ratio"],
                "Max Drawdown": result.metrics["max_drawdown"],
                "Win Rate": result.metrics["win_rate"],
                "Profit Factor": result.metrics["profit_factor"],
                "Trades": result.metrics["total_trades"],
                "Final Equity": result.metrics["final_equity"],
            }
        )

    comparison = pd.DataFrame(rows)

    if not comparison.empty:
        comparison = comparison.sort_values(
            by=["Sharpe Ratio", "Total Return"],
            ascending=[False, False],
            na_position="last",
        ).reset_index(drop=True)
        comparison.index = comparison.index + 1
        comparison.index.name = "Rank"

    return comparison, results
