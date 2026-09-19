from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CORE_TABLES = {
    "paper_accounts",
    "paper_positions",
    "paper_orders",
    "paper_trades",
    "paper_position_lots",
    "paper_trade_entry_links",
    "paper_journal",
    "paper_account_snapshots",
}

@dataclass(frozen=True)
class DatabaseHealth:
    ok: bool
    integrity: str
    foreign_key_violations: int
    missing_core_tables: tuple[str, ...]
    orphan_positions: int
    orphan_orders: int
    orphan_trades: int

    @property
    def issues(self) -> tuple[str, ...]:
        items: list[str] = []
        if self.integrity.lower() != "ok":
            items.append(f"SQLite integrity check: {self.integrity}")
        if self.foreign_key_violations:
            items.append(f"{self.foreign_key_violations} foreign-key violation(s)")
        if self.missing_core_tables:
            items.append("Missing core tables: " + ", ".join(self.missing_core_tables))
        for label, count in (("orphan positions", self.orphan_positions), ("orphan orders", self.orphan_orders), ("orphan trades", self.orphan_trades)):
            if count:
                items.append(f"{count} {label}")
        return tuple(items)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def database_health(db_path: str | Path) -> DatabaseHealth:
    path = Path(db_path)
    if not path.exists():
        return DatabaseHealth(False, "database file missing", 0, tuple(sorted(CORE_TABLES)), 0, 0, 0)
    try:
        with _connect(path) as conn:
            integrity_row = conn.execute("PRAGMA integrity_check").fetchone()
            integrity = str(integrity_row[0]) if integrity_row else "no result"
            fk_violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = tuple(sorted(CORE_TABLES - tables))
            def orphan(child: str) -> int:
                if child not in tables or "paper_accounts" not in tables:
                    return 0
                return int(conn.execute(
                    f"SELECT COUNT(*) FROM {child} c LEFT JOIN paper_accounts a ON a.id=c.account_id WHERE a.id IS NULL"
                ).fetchone()[0])
            positions = orphan("paper_positions")
            orders = orphan("paper_orders")
            trades = orphan("paper_trades")
        ok = integrity.lower() == "ok" and fk_violations == 0 and not missing and not any((positions, orders, trades))
        return DatabaseHealth(ok, integrity, fk_violations, missing, positions, orders, trades)
    except sqlite3.DatabaseError as exc:
        return DatabaseHealth(False, f"database error: {exc}", 0, (), 0, 0, 0)


def create_database_backup(db_path: str | Path, backup_dir: str | Path | None = None) -> Path:
    source = Path(db_path)
    if not source.exists():
        raise FileNotFoundError(source)
    destination_dir = Path(backup_dir) if backup_dir else source.parent / "backups"
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_dir / f"{source.stem}_{stamp}.db"
    # SQLite's backup API creates a transactionally consistent copy even when WAL is in use.
    with _connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return destination


def restore_database_backup(db_path: str | Path, backup_path: str | Path) -> Path:
    target, backup = Path(db_path), Path(backup_path)
    if not backup.exists():
        raise FileNotFoundError(backup)
    health = database_health(backup)
    if not health.ok:
        raise ValueError("Refusing to restore an unhealthy backup: " + "; ".join(health.issues))
    target.parent.mkdir(parents=True, exist_ok=True)
    safety_copy = target.with_suffix(target.suffix + ".pre_restore")
    if target.exists():
        shutil.copy2(target, safety_copy)
    shutil.copy2(backup, target)
    return safety_copy
