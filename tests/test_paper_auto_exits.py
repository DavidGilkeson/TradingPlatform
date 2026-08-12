import pytest

from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.auto_exits import (
    AutomaticExitService,
    evaluate_auto_exit_for_position,
)
from paper_trading.exit_plans import ExitPlanRepository


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "auto_exits.db"


def test_stop_loss_trigger():
    reason = evaluate_auto_exit_for_position(
        ticker="AAPL",
        entry_price=100,
        current_price=94,
        stop_price=95,
        target_price=110,
    )
    assert reason == "STOP_LOSS"


def test_take_profit_trigger():
    reason = evaluate_auto_exit_for_position(
        ticker="AAPL",
        entry_price=100,
        current_price=111,
        stop_price=95,
        target_price=110,
    )
    assert reason == "TAKE_PROFIT"


def test_no_trigger_between_levels():
    reason = evaluate_auto_exit_for_position(
        ticker="AAPL",
        entry_price=100,
        current_price=103,
        stop_price=95,
        target_price=110,
    )
    assert reason is None


def test_disabled_auto_exit_does_nothing(db_path):
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10000)

    orders = PaperOrderService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )
    orders.buy_market(
        ticker="AAPL",
        shares=10,
        market_price=100,
    )

    account = account_service.active_account()
    plans = ExitPlanRepository(str(db_path))
    plans.save_plan(
        account_id=account.id,
        ticker="AAPL",
        stop_price=95,
        target_price=110,
    )

    account_service.update_market_prices({"AAPL": 94})

    service = AutomaticExitService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )

    events = service.process_triggered_exits(enabled=False)

    assert events == []
    assert len(
        account_service.repository.list_positions(account.id)
    ) == 1


def test_enabled_stop_loss_closes_position(db_path):
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10000)

    orders = PaperOrderService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )
    orders.buy_market(
        ticker="AAPL",
        shares=10,
        market_price=100,
    )

    account = account_service.active_account()
    plans = ExitPlanRepository(str(db_path))
    plans.save_plan(
        account_id=account.id,
        ticker="AAPL",
        stop_price=95,
        target_price=110,
    )

    account_service.update_market_prices({"AAPL": 94})

    service = AutomaticExitService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )

    events = service.process_triggered_exits(enabled=True)

    assert len(events) == 1
    assert events[0].exit_reason == "STOP_LOSS"
    assert events[0].realised_pnl == pytest.approx(-60)

    account = account_service.active_account()
    assert account_service.repository.list_positions(account.id) == []
    assert plans.get_plan(
        account_id=account.id,
        ticker="AAPL",
    ) is None


def test_enabled_take_profit_closes_position(db_path):
    account_service = PaperAccountService(str(db_path))
    account_service.initialise_account(starting_balance=10000)

    orders = PaperOrderService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )
    orders.buy_market(
        ticker="MSFT",
        shares=5,
        market_price=200,
    )

    account = account_service.active_account()
    plans = ExitPlanRepository(str(db_path))
    plans.save_plan(
        account_id=account.id,
        ticker="MSFT",
        stop_price=190,
        target_price=220,
    )

    account_service.update_market_prices({"MSFT": 225})

    service = AutomaticExitService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )

    events = service.process_triggered_exits(enabled=True)

    assert len(events) == 1
    assert events[0].exit_reason == "TAKE_PROFIT"
    assert events[0].realised_pnl == pytest.approx(125)
