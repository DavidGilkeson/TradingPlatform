# Project Atlas — Sprint 31.6 Order Ticket Intelligence

The evidence-based historical scorecard now appears directly inside the BUY
paper-order workflow.

Before submitting a BUY, Atlas uses the current scanner context plus the
trader's confidence and reason to compare the proposed setup with completed
paper trades.

When a BUY fills, Atlas stores an immutable entry-time intelligence snapshot
linked to the paper order. The snapshot includes:

- Atlas Score
- confidence
- trend and volatility regime when derivable from scanner data
- historical match score
- number of similar completed trades
- historical win rate and expectancy
- evidence/sample grades
- reliability
- historical verdict

This gives future analytics a clean answer to: did setups that looked strong
at entry actually perform better later?

The scorecard remains descriptive paper-trading evidence, not a live-trading
recommendation.
