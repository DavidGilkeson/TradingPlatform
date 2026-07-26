# Atlas Strategy Framework

## Purpose

The strategy framework gives every Atlas trading strategy the same interface.
A strategy validates market data, generates `BUY`, `SELL`, and `HOLD` signals,
and returns a standard `StrategyResult`.

## Package structure

```text
strategies/
├── __init__.py
├── base_strategy.py
├── registry.py
├── strategy_loader.py
├── moving_average.py
├── rsi_pullback.py
├── momentum.py
└── atlas_composite.py
```

## Running a strategy

```python
from strategies import get_strategy

strategy = get_strategy("atlas_composite")
result = strategy.run(price_data)

print(result.summary())
print(result.signals.tail())
```

## Adding another strategy

1. Create a class that inherits from `BaseStrategy`.
2. Implement `generate_signals()`.
3. Ensure the returned DataFrame contains `Signal`.
4. Register its factory in `strategies/registry.py`.
5. Add unit tests.

## Streamlit integration

Import the reusable component:

```python
from strategy_framework_ui import display_strategy_framework
```

Inside your Strategy Lab tab:

```python
display_strategy_framework(
    ticker=strategy_ticker,
    selected_data=strategy_data,
)
```

This framework generates trading signals only. Performance metrics and trade
simulation belong in the universal backtesting engine planned for Sprint 28.2.
