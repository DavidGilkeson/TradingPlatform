# Atlas Sprint 35.1 — Error Handling & Recovery

Built from Sprint 35.0.

## Added
- `paper_trading/resilience.py`: typed recovery results, safe operational calls, friendly connection/database/file messages, and read-only database preflight.
- `paper_trading/recovery_ui.py`: reusable Streamlit recovery presentation.
- `SCANNER_CONNECTION_RECOVERY_PATCH.md`: specific handling guidance for the observed `DownloadButton: not connected to a server!` case.
- `tests/test_error_recovery.py`: connection, timeout, missing DB, and valid DB recovery tests.

## Safety behaviour
Recovery is non-destructive. Atlas does not delete, recreate, or silently repair paper-trading data when an operational failure occurs.

## Verification
- `python -m compileall -q .` passed.
- `PYTHONPATH=. python -m pytest -q` → **253 passed, 1 pre-existing pandas FutureWarning**.
