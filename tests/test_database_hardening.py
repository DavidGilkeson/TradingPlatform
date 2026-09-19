import sqlite3
from pathlib import Path

import pytest

from paper_trading.database import PaperTradingDatabase
from paper_trading.database_health import database_health, create_database_backup, restore_database_backup


def test_new_database_is_healthy(tmp_path):
    db = PaperTradingDatabase(tmp_path / "paper.db")
    health = db.health_check()
    assert health.ok
    assert health.integrity == "ok"
    assert not health.issues


def test_database_connection_enforces_safety_pragmas(tmp_path):
    db = PaperTradingDatabase(tmp_path / "paper.db")
    with db.connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 35


def test_health_detects_missing_core_tables(tmp_path):
    path = tmp_path / "partial.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE paper_accounts(id INTEGER PRIMARY KEY)")
    health = database_health(path)
    assert not health.ok
    assert "paper_orders" in health.missing_core_tables


def test_backup_is_healthy_and_preserves_data(tmp_path):
    db = PaperTradingDatabase(tmp_path / "paper.db")
    with db.connect() as conn:
        conn.execute("INSERT INTO paper_accounts(name,starting_balance,cash,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("Main",10000,10000,1,"2026-01-01","2026-01-01"))
    backup = db.backup(tmp_path / "backups")
    assert backup.exists()
    assert database_health(backup).ok
    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT name FROM paper_accounts").fetchone()[0] == "Main"


def test_restore_refuses_unhealthy_backup(tmp_path):
    target = tmp_path / "paper.db"
    PaperTradingDatabase(target)
    bad = tmp_path / "bad.db"
    with sqlite3.connect(bad) as conn:
        conn.execute("CREATE TABLE nope(id INTEGER)")
    with pytest.raises(ValueError):
        restore_database_backup(target, bad)
