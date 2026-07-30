"""Public API for the Atlas universal backtesting engine."""

from .comparison import compare_strategies
from .equity_curve import calculate_drawdown, daily_returns
from .metrics import calculate_metrics
from .models import BacktestConfig, BacktestResult, OpenPosition, Trade
from .runner import backtest_strategy
from .simulator import run_backtest

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "OpenPosition",
    "Trade",
    "backtest_strategy",
    "calculate_drawdown",
    "calculate_metrics",
    "compare_strategies",
    "daily_returns",
    "run_backtest",
]
