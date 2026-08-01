"""Tests for Sprint 29.2 paper order execution."""

from __future__ import annotations

import pytest

from paper_trading import PaperAccountService, PaperOrderService


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "paper_orders.db"


def test_market_buy_reduces_cash_and_creates_position(db_path) -> None:
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10_000)

    service = PaperOrderService(
        str(db_path),
        commission=5,
        slippage_pct=0.01,
    )
    execution = service.buy_market(
        ticker="AAPL",
        shares=10,
        market_price=100,
        reason="Atlas Buy",
    )

    account = account_service.active_account()
    positions = account_service.repository.list_positions(account.id)

    assert execution.filled_price == pytest.approx(101)
    assert account.cash == pytest.approx(8_985)
    assert len(positions) == 1
    assert positions[0].shares == 10


def test_second_buy_updates_weighted_average(db_path) -> None:
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10_000)
    service = PaperOrderService(str(db_path), commission=0, slippage_pct=0)

    service.buy_market(ticker="MSFT", shares=5, market_price=100)
    service.buy_market(ticker="MSFT", shares=5, market_price=120)

    account = account_service.active_account()
    position = account_service.repository.list_positions(account.id)[0]

    assert position.shares == 10
    assert position.average_entry_price == pytest.approx(110)


def test_buy_rejects_insufficient_cash(db_path) -> None:
    PaperAccountService(str(db_path)).initialise_account(starting_balance=1_000)
    service = PaperOrderService(str(db_path))

    with pytest.raises(ValueError, match="Insufficient buying power"):
        service.buy_market(ticker="NVDA", shares=20, market_price=100)


def test_partial_sell_reduces_position_and_realises_pnl(db_path) -> None:
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10_000)
    service = PaperOrderService(str(db_path), commission=0, slippage_pct=0)

    service.buy_market(ticker="AAPL", shares=10, market_price=100)
    execution = service.sell_market(
        ticker="AAPL",
        shares=4,
        market_price=120,
    )

    account = account_service.active_account()
    position = account_service.repository.list_positions(account.id)[0]

    assert execution.realised_pnl == pytest.approx(80)
    assert position.shares == pytest.approx(6)
    assert account.cash == pytest.approx(9_480)


def test_full_sell_closes_position(db_path) -> None:
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10_000)
    service = PaperOrderService(str(db_path), commission=0, slippage_pct=0)

    service.buy_market(ticker="AMD", shares=10, market_price=100)
    service.sell_market(ticker="AMD", shares=10, market_price=90)

    account = account_service.active_account()

    assert account_service.repository.list_positions(account.id) == []
    assert account.cash == pytest.approx(9_900)
    assert account_service.snapshot(False).realised_pnl == pytest.approx(-100)


def test_sell_rejects_more_than_held(db_path) -> None:
    PaperAccountService(str(db_path)).initialise_account()
    service = PaperOrderService(str(db_path))

    service.buy_market(ticker="META", shares=2, market_price=100)

    with pytest.raises(ValueError, match="Only 2 shares"):
        service.sell_market(ticker="META", shares=3, market_price=110)


def test_sell_rejects_missing_position(db_path) -> None:
    PaperAccountService(str(db_path)).initialise_account()
    service = PaperOrderService(str(db_path))

    with pytest.raises(ValueError, match="No open TSLA position"):
        service.sell_market(ticker="TSLA", shares=1, market_price=200)


def test_orders_and_journal_are_persisted(db_path) -> None:
    PaperAccountService(str(db_path)).initialise_account()
    service = PaperOrderService(str(db_path))

    execution = service.buy_market(
        ticker="GOOGL",
        shares=1,
        market_price=150,
        reason="Strong Buy",
        notes="Test entry",
        confidence=8,
        atlas_score=91,
    )

    orders = service.list_orders()

    with service.database.connect() as connection:
        journal = connection.execute(
            "SELECT * FROM paper_journal WHERE order_id = ?",
            (execution.order_id,),
        ).fetchone()

    assert len(orders) == 1
    assert orders[0]["status"] == "FILLED"
    assert journal["reason"] == "Strong Buy"
    assert journal["confidence"] == 8
    assert journal["atlas_score"] == 91


def test_slippage_and_commission_reduce_sell_proceeds(db_path) -> None:
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10_000)
    service = PaperOrderService(
        str(db_path),
        commission=5,
        slippage_pct=0.01,
    )

    service.buy_market(ticker="AAPL", shares=10, market_price=100)
    execution = service.sell_market(
        ticker="AAPL",
        shares=10,
        market_price=110,
    )

    assert execution.filled_price == pytest.approx(108.9)
    assert execution.cash_after < 10_000 + 89
