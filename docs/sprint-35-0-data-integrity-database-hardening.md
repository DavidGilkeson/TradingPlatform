# Sprint 35.0 — Data Integrity & Database Hardening

Sprint 35 begins the Atlas v1.0 hardening phase. This sprint adds defensive SQLite settings, explicit schema version tracking, health checks, and transactionally consistent backups.

## Database safeguards

- Foreign keys are enforced on every Atlas paper-trading connection.
- WAL journaling improves resilience and read/write concurrency.
- A 5-second busy timeout reduces avoidable `database is locked` failures.
- `PRAGMA user_version = 35` establishes a migration/version anchor for the hardening phase.
- Existing databases remain compatible because the core schema continues to use idempotent `CREATE TABLE IF NOT EXISTS` statements.

## Health checks

`paper_trading.database_health.database_health()` checks SQLite integrity, foreign-key violations, missing core tables, and orphaned account-owned positions/orders/trades. It returns structured results rather than silently repairing data.

## Backup and restore

`create_database_backup()` uses SQLite's backup API, making a consistent copy even when WAL mode is active. `restore_database_backup()` validates a backup before restoring it and keeps a `.pre_restore` safety copy of the current database.

Atlas does not automatically delete or repair suspicious records. Hardening should protect paper-trading evidence rather than conceal inconsistencies.
