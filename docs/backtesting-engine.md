# Atlas Universal Backtesting Engine

## Overview

The universal backtester accepts signals from any Atlas strategy and converts
them into completed trades, an equity curve, drawdowns, and professional
performance metrics.

## Package structure

```text
backtesting/
├── __init__.py
├── models.py
├── simulator.py
├── runner.py
├── metrics.py
├── equity_curve.py
├── comparison.py
└── visualisations.py
```

## Single strategy example

```python
from strategies import get_strategy
from backtesting import BacktestConfig, backtest_strategy

strategy = get_strategy("atlas_composite")

config = BacktestConfig(
    ticker="AAPL",
    initial_capital=10_000,
    position_size_pct=1.0,
    commission=0,
    slippage_pct=0.001,
)

result = backtest_strategy(strategy, price_data, config=config)

print(result.summary())
print(result.trades_frame())
```

## Strategy comparison

```python
from strategies import load_strategies
from backtesting import compare_strategies

leaderboard, results = compare_strategies(
    load_strategies(),
    price_data,
    config=config,
)
```

## Streamlit integration

```python
from backtesting_ui import display_backtesting_lab

display_backtesting_lab(
    ticker=selected_ticker,
    market_data=historical_price_data,
)
```

## Current execution model

- Long-only
- One position at a time
- Orders execute at the current row's closing price
- Configurable percentage position sizing
- Configurable fixed commission per order
- Configurable percentage slippage
- Open positions can be closed automatically at the end of the dataset

This model is deliberately transparent and deterministic. Future versions can
add next-bar execution, stop losses, take profits, short selling, portfolio
allocation, and multi-asset simulation.
