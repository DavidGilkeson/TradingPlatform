"""Release-candidate edge cases for Atlas safety and recovery paths."""
import math
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from atlas_cache import TTLCache
from paper_trading.database import PaperTradingDatabase
from paper_trading.database_health import database_health, create_database_backup, restore_database_backup
from paper_trading.resilience import database_available, safe_call
from paper_trading.risk_manager import calculate_position_size, validate_order_risk
from paper_trading.trade_readiness import assess_trade_readiness


def test_cache_concurrent_reads_and_writes_remain_bounded():
    cache = TTLCache(ttl_seconds=30, max_entries=8)

    def worker(i):
        cache.set(f"key-{i % 16}", {"value": i})
        cache.get(f"key-{(i + 1) % 16}")
        return cache.info().entries

    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(worker, range(200)))
    assert all(0 <= count <= 8 for count in counts)
    assert cache.info().entries <= 8


def test_cache_does_not_cache_exceptions():
    cache = TTLCache()
    calls = []

    def fail_once_then_succeed():
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError("temporary market data outage")
        return 123.45

    with pytest.raises(TimeoutError):
        cache.get_or_compute("AAPL", fail_once_then_succeed)
    assert cache.get_or_compute("AAPL", fail_once_then_succeed) == 123.45
    assert cache.get_or_compute("AAPL", fail_once_then_succeed) == 123.45
    assert len(calls) == 2


def test_cache_supports_tuple_keys_and_nested_mutable_values():
    cache = TTLCache()
    cache.set(("price", "AAPL"), {"quote": [100.0]})
    first = cache.get(("price", "AAPL"))
    first["quote"].append(999.0)
    assert cache.get(("price", "AAPL")) == {"quote": [100.0]}


def test_database_preflight_does_not_create_missing_database(tmp_path):
    path = tmp_path / "missing.db"
    result = database_available(path)
    assert not result.ok
    assert result.value is False
    assert not path.exists()


def test_database_preflight_reports_corrupt_database_without_replacing_it(tmp_path):
    path = tmp_path / "corrupt.db"
    path.write_bytes(b"not a sqlite database")
    original = path.read_bytes()
    result = database_available(path)
    assert not result.ok
    assert path.read_bytes() == original


def test_database_health_reports_missing_database_without_creating_it(tmp_path):
    path = tmp_path / "absent.db"
    health = database_health(path)
    assert not health.ok
    assert "missing" in health.integrity
    assert not path.exists()


def test_database_rejects_non_positive_position_shares(tmp_path):
    db = PaperTradingDatabase(tmp_path / "paper.db")
    with db.connect() as conn:
        account_id = conn.execute(
            "INSERT INTO paper_accounts(name,starting_balance,cash,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("Test", 10000, 10000, 1, "2026-01-01", "2026-01-01"),
        ).lastrowid
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO paper_positions(account_id,ticker,shares,average_entry_price,current_price,opened_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (account_id, "AAPL", 0, 100, 100, "2026-01-01", "2026-01-01"),
            )


def test_backup_and_restore_preserve_safety_copy(tmp_path):
    target = tmp_path / "paper.db"
    db = PaperTradingDatabase(target)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO paper_accounts(name,starting_balance,cash,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("Original", 10000, 10000, 1, "2026-01-01", "2026-01-01"),
        )
    backup = create_database_backup(target, tmp_path / "backups")
    with db.connect() as conn:
        conn.execute("UPDATE paper_accounts SET name='Changed'")
    safety_copy = restore_database_backup(target, backup)
    assert safety_copy.exists()
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT name FROM paper_accounts").fetchone()[0] == "Original"
    with sqlite3.connect(safety_copy) as conn:
        assert conn.execute("SELECT name FROM paper_accounts").fetchone()[0] == "Changed"


def test_safe_call_converts_expected_timeout_to_recovery_result():
    result = safe_call(lambda: (_ for _ in ()).throw(TimeoutError()), context="Scanner")
    assert not result.ok
    assert result.error_type == "TimeoutError"
    assert "Refresh" in result.recovery


def test_safe_call_does_not_hide_programming_errors():
    with pytest.raises(ZeroDivisionError):
        safe_call(lambda: 1 / 0)


def test_position_sizing_rejects_nan_and_infinite_inputs():
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            calculate_position_size(
                account_equity=10000, entry_price=100, stop_price=95,
                risk_pct=value,
            )


def test_order_risk_blocks_non_finite_values():
    result = validate_order_risk(
        account_equity=10000, cash=10000, shares=math.nan,
        entry_price=100, stop_price=95,
    )
    assert not result.allowed
    assert any("finite" in blocker for blocker in result.blockers)


def test_order_risk_blocks_negative_cash_and_invalid_prices():
    negative_cash = validate_order_risk(
        account_equity=10000, cash=-1, shares=1, entry_price=100, stop_price=95,
    )
    assert not negative_cash.allowed
    assert any("cash" in blocker.lower() for blocker in negative_cash.blockers)

    invalid_price = validate_order_risk(
        account_equity=10000, cash=10000, shares=1, entry_price=0, stop_price=0,
    )
    assert not invalid_price.allowed
    assert any("prices" in blocker.lower() for blocker in invalid_price.blockers)


def test_readiness_treats_nan_score_and_reward_risk_as_missing():
    result = assess_trade_readiness(
        has_market_price=True,
        thesis="Breakout with volume confirmation",
        invalidation="Close below support",
        risk_allowed=True,
        guardrails_allowed=True,
        planned_rr=math.nan,
        minimum_rr=2.0,
        atlas_score=math.nan,
        confirmed=True,
    )
    assert result["status"] == "Not Ready"
    assert any("Reward/risk" in blocker for blocker in result["blockers"])
    assert any("Atlas score" in caution for caution in result["cautions"])


def test_position_sizing_caps_exposure_even_when_risk_budget_is_large():
    plan = calculate_position_size(
        account_equity=10000, entry_price=100, stop_price=99,
        risk_pct=10, max_position_pct=20,
    )
    assert plan.position_value <= 2000
    assert plan.position_pct <= 20
