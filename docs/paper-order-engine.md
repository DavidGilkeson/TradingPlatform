# Atlas Sprint 29.2 — Paper Order Engine

Sprint 29.2 turns the persistent virtual account into an interactive paper
broker.

## Features

- Market BUY orders
- Market SELL orders
- Cash and buying-power validation
- Slippage and fixed commission
- Weighted-average entry price when adding to a position
- Partial and full exits
- Realised P&L
- Completed trade records
- Filled order history
- Automatic journal entries
- Atlas Score, reason, confidence, and notes captured at order time
- Streamlit order ticket
- Automatic mark-to-market updates from scanner data

## Updated app integration

Pass the scanner DataFrame to the dashboard:

```python
with paper_tab:
    display_paper_trading_dashboard(
        db_path="data/paper_trading.db",
        market_df=df,
    )
```

## Test

```bash
pytest tests/test_paper_order_engine.py -v
```
