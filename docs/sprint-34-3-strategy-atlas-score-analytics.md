# Sprint 34.3 — Strategy & Atlas Score Analytics

Adds evidence-aware outcome analysis for Atlas intelligence captured at the exact time of entry.

## What changed
- Links completed trades to exact BUY orders through `paper_trade_entry_links`.
- Uses immutable entry-time `paper_intelligence_snapshots`, not later scanner state.
- Analyses outcomes by Atlas Score band, entry confidence and historical verdict.
- Handles scaled entries by allocating realised P&L using entry-link weights.
- Adds minimum sample/evidence thresholds and sample-quality labels.
- Adds a descriptive score/outcome relationship check only when 3+ score bands exist.

The analytics are observational and do not automatically approve, reject, size or execute trades.
