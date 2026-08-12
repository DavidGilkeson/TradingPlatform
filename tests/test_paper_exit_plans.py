import pytest

from paper_trading import PaperAccountService
from paper_trading.exit_plans import (
    ExitPlanRepository,
    evaluate_exit_plan,
    validate_exit_plan,
)


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "exit_plans.db"


def test_exit_plan_roundtrip(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account()

    repo = ExitPlanRepository(str(db_path))

    saved = repo.save_plan(
        account_id=account.id,
        ticker="AAPL",
        stop_price=95,
        target_price=110,
    )

    loaded = repo.get_plan(
        account_id=account.id,
        ticker="AAPL",
    )

    assert saved.ticker == "AAPL"
    assert loaded is not None
    assert loaded.stop_price == 95
    assert loaded.target_price == 110


def test_exit_plan_delete(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account()
    repo = ExitPlanRepository(str(db_path))

    repo.save_plan(
        account_id=account.id,
        ticker="MSFT",
        stop_price=190,
        target_price=220,
    )

    repo.delete_plan(
        account_id=account.id,
        ticker="MSFT",
    )

    assert repo.get_plan(
        account_id=account.id,
        ticker="MSFT",
    ) is None


def test_validate_rejects_stop_above_entry():
    with pytest.raises(ValueError):
        validate_exit_plan(
            entry_price=100,
            stop_price=101,
            target_price=110,
        )


def test_validate_rejects_target_below_entry():
    with pytest.raises(ValueError):
        validate_exit_plan(
            entry_price=100,
            stop_price=95,
            target_price=99,
        )


def test_exit_status_active():
    status = evaluate_exit_plan(
        ticker="AAPL",
        entry_price=100,
        current_price=103,
        stop_price=95,
        target_price=110,
    )

    assert not status.stop_triggered
    assert not status.target_triggered
    assert status.reward_risk_ratio == pytest.approx(2)


def test_exit_status_stop_triggered():
    status = evaluate_exit_plan(
        ticker="AAPL",
        entry_price=100,
        current_price=94,
        stop_price=95,
        target_price=110,
    )

    assert status.stop_triggered


def test_exit_status_target_triggered():
    status = evaluate_exit_plan(
        ticker="AAPL",
        entry_price=100,
        current_price=111,
        stop_price=95,
        target_price=110,
    )

    assert status.target_triggered
