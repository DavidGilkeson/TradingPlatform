# Project Atlas — Sprint 33.1

Structured Pre-Trade Thesis & Risk Plan is live.

Before a Paper BUY, Atlas now captures and permanently links the plan to the
actual filled buy order:

- written trade thesis
- thesis invalidation condition
- actual filled entry price
- stop-loss
- take-profit target
- planned shares
- account risk %
- maximum position %
- minimum acceptable reward/risk
- calculated planned reward/risk
- trader confidence
- Atlas score
- entry-time market regime
- entry-time volatility regime

A BUY now requires a written thesis. This makes the journal useful for
prospective learning rather than allowing the rationale to be reconstructed
after seeing the outcome.

Trade plans are stored in `paper_trade_plans` and linked by `buy_order_id`.
Existing databases are unaffected because the table is created lazily and
safely.

Next: Sprint 33.2 — Plan vs Outcome Review. Link completed trades back to their
entry plans and automatically show planned entry/stop/target/R:R beside actual
return, P&L and post-trade execution review.
