# Atlas Sprint 29.1 — Paper Trading Foundation

Adds a persistent SQLite-backed virtual account, open positions, mark-to-market
valuation, snapshots, realised/unrealised P&L, reset workflow, Streamlit UI,
and tests.

## Integration

```python
from paper_trading_ui import display_paper_trading_dashboard

with paper_tab:
    display_paper_trading_dashboard("data/paper_trading.db")
```

Sprint 29.2 adds validated BUY and SELL market orders, execution costs, order
history, completed trades, and automatic journal entries.
