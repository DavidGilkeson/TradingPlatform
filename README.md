# Project Atlas — Sprint 33.2

Plan vs Outcome Review is live.

The Post-Trade Journal now retrieves the immutable structured entry plan and
places it beside the completed result.

Planned:
- entry
- stop
- target
- reward/risk
- original thesis
- original invalidation

Actual:
- exit
- return %
- realised P&L
- outcome relative to the planned stop/target range

Atlas classifies completed outcomes as target reached/exceeded, stop
reached/breached, profitable or losing exit inside the plan range, or
break-even.

The comparison uses exact `paper_trade_entry_links` lineage instead of guessing
which BUY created the completed trade. Multi-entry trades use the
largest-weight linked plan as the primary display and are clearly identified.

Legacy trades opened before Sprint 33.1 remain supported.

Next: Sprint 33.3 — Plan Adherence Analytics.
