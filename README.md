# Atlas Strategy Framework — Sprint 28.1

This package introduces a modular strategy architecture for Project Atlas.

Included strategies:

- Moving Average Cross
- RSI Pullback
- Momentum
- Atlas Composite

It also includes:

- a common `BaseStrategy` interface
- a standard `StrategyResult`
- a central strategy registry
- strategy loading helpers
- a reusable Streamlit component
- unit tests
- integration documentation

## Install test dependencies

```bash
pip install pandas numpy pytest
```

## Run tests

```bash
pytest tests/test_strategy_framework.py -v
```

## Copy into Atlas

Copy these into the root of the Atlas repository:

```text
strategies/
strategy_framework_ui.py
tests/test_strategy_framework.py
docs/strategy-framework.md
```
