# Project Atlas — Sprint 31.2 Sample Quality & Pattern Confidence

Sprint 31.2 adds safeguards against drawing strong conclusions from tiny
paper-trading samples.

Atlas now assigns every intelligence pattern:

- sample grade
- evidence level
- 0–100 sample-size reliability score
- Insight Ready status
- small-sample warning

Default evidence threshold: 10 completed trades per pattern.

A pattern with very high expectancy from only one or two trades can still be
displayed, but Atlas will not promote it as an evidence-qualified leader until
it passes the chosen threshold.

The reliability score measures sample quantity only. It is not a prediction of
future profitability and is not a statistical guarantee.
