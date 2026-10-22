# Sprint 35.3 — Full Regression & Edge-Case Testing

## Summary
This sprint adds release-candidate coverage around cache concurrency and failures, database preflight/backup/restore, risk-input boundaries, and readiness scoring. Testing exposed a real SQLite restore edge case: byte-copying a database file can miss committed pages held in the WAL. Restore now uses SQLite's backup API for both the pre-restore safety copy and the validated backup restore, then verifies the resulting database.

## Coverage added
- Threaded TTL cache reads/writes remain within configured capacity.
- Cache computation exceptions are not cached; a transient failure can be retried.
- Tuple keys and nested mutable cache values remain isolated from caller mutation.
- Missing/corrupt database preflight is non-creating and non-destructive.
- Database CHECK constraints reject zero-share positions.
- Backup/restore retains the intended restored state and a separate pre-restore safety copy.
- Expected connection failures produce actionable recovery results, while programming errors still surface.
- Position sizing rejects NaN/infinite inputs.
- Order risk validation blocks non-finite inputs, negative cash, and invalid prices.
- Trade readiness treats NaN score and reward/risk values as missing evidence.
- Exposure caps remain effective when the risk budget would otherwise permit a larger position.

## Safety changes
- `calculate_position_size` rejects non-finite risk inputs.
- `validate_order_risk` explicitly blocks non-finite values, invalid equity/cash/prices, and invalid risk limits.
- `assess_trade_readiness` no longer treats NaN/Infinity as valid numeric evidence.
- `restore_database_backup` uses SQLite's backup API to account for WAL journaling and validates the safety copy and restored database.

## Validation
Run from the project root:

```bash
python -m compileall -q .
python -m pytest -q
```

Result for this sprint: **274 passed, 1 existing pandas FutureWarning**.

## Existing warning
One pre-existing warning remains in `tests/test_adherence_analytics.py::test_unreviewed_follow_plan_excluded`: a pandas boolean column is assigned `NaN`. It does not fail the suite, but should be corrected in a focused analytics cleanup rather than silently changing the test's semantics in this hardening sprint.

## Scope
This is a local code/test hardening sprint. It does not certify the application against every broker, provider, operating system, or real-market failure. Continue using paper trading only while collecting evidence; do not connect live order execution as part of this sprint.
