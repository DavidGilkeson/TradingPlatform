# Atlas Sprint 29.6 — One-Click Trading & Smart Watchlist

Sprint 29.6 connects Atlas market intelligence with the paper order ticket.

## Features

- Watchlist enriched with scanner data
- Ranked by Atlas Score
- Quick paper BUY queue
- Ticker, side, reason, notes, and share amount passed into Paper Trading
- Order ticket preselects the queued trade
- Queue is cleared after a successful simulated fill

## Integration

Add this where you want the smarter watchlist to appear:

```python
from paper_trading.watchlist_ui import display_smart_watchlist

display_smart_watchlist(
    watchlist=watchlist,
    market_df=df,
)
```

The Paper Trading tab itself needs no extra changes.
