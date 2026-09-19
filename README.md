# Atlas Sprint 34.3 — Strategy & Atlas Score Analytics

Builds on Sprint 34.2 and adds evidence-aware analysis of Atlas intelligence captured at the exact paper-trade entry.

Highlights:
- exact BUY-order lineage via `paper_trade_entry_links`
- immutable entry-time intelligence snapshots
- Atlas Score-band, confidence and entry-verdict outcome analytics
- scaled-entry P&L allocation
- minimum sample/evidence thresholds
- descriptive score/outcome relationship check

Regression: **239 tests passed**, with 1 pre-existing pandas FutureWarning.
