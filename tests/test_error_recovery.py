import sqlite3
from paper_trading.resilience import database_available, friendly_error, safe_call


def test_connection_error_has_reconnect_guidance():
    r = friendly_error(ConnectionError("offline"), context="Atlas")
    assert not r.ok
    assert "connection" in r.message.lower()
    assert "refresh" in r.recovery.lower()


def test_safe_call_returns_success_value():
    r = safe_call(lambda x: x + 1, 4)
    assert r.ok and r.value == 5


def test_safe_call_contains_known_operational_failure():
    def boom():
        raise TimeoutError("slow")
    r = safe_call(boom, context="Market data")
    assert not r.ok
    assert r.error_type == "TimeoutError"
    assert "market data" in r.message.lower()


def test_database_available_does_not_create_missing_db(tmp_path):
    p = tmp_path / "missing.db"
    r = database_available(p)
    assert not r.ok and r.value is False
    assert not p.exists()


def test_database_available_accepts_valid_db(tmp_path):
    p = tmp_path / "paper.db"
    con = sqlite3.connect(p)
    con.execute("create table demo(id integer primary key)")
    con.commit(); con.close()
    r = database_available(p)
    assert r.ok and r.value is True
