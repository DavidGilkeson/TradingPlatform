# Atlas Sprint 29.3 — Live Portfolio Dashboard

Adds live equity, cash/invested split, realised and unrealised P&L, winners and
losers, allocation charts, concentration/diversification scoring, and position
drill-down with entry context from the paper journal.

The existing app integration remains:

```python
with paper_tab:
    display_paper_trading_dashboard(
        db_path="data/paper_trading.db",
        market_df=df,
    )
```
