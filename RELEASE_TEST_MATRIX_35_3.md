# Atlas Release Test Matrix — Sprint 35.3

| Area | Edge case | Expected result |
|---|---|---|
| Cache | Concurrent set/get | Bounded entry count; no thread errors |
| Cache | Compute raises timeout | Exception propagates; later call can retry |
| Cache | Caller mutates nested return value | Cached value remains unchanged |
| Database | Configured path missing | Read-only preflight reports missing; does not create file |
| Database | Corrupt bytes at database path | Preflight reports failure; file remains unchanged |
| Database | Invalid position shares | SQLite constraint rejects write |
| Database | Restore with WAL-mode target | Restored database validated; pre-restore state preserved |
| Recovery | Timeout / connection failure | Actionable recovery result |
| Recovery | Programming exception | Not hidden by generic recovery wrapper |
| Risk | NaN or infinity | Sizing raises validation error; order validator blocks |
| Risk | Negative cash / non-positive prices | Order is blocked with a reason |
| Readiness | NaN Atlas score or R:R | Treated as missing evidence; cannot qualify as ready |
| Exposure | Risk budget exceeds exposure limit | Share count still respects position cap |

## Manual smoke test before release
1. Start Atlas with the normal Streamlit command.
2. Load the scanner and confirm the app renders when market data is unavailable.
3. Open Paper Trading and inspect account, open positions, journal, and performance views.
4. Create a paper order with a valid plan and verify readiness checks are visible.
5. Try an invalid or non-finite risk input through the relevant validation path; confirm the order is blocked rather than accepted.
6. Run Database Health and create a backup.
7. Test restore only against a disposable copy of the database; verify both restored data and `.pre_restore` safety copy.
8. Disconnect or stop the Streamlit process and confirm the UI's recovery guidance is clear after reconnection.
9. Re-run the full pytest suite before tagging a release candidate.
