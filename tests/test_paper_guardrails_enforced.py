
import pytest

from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.portfolio_guardrails import (
    GuardrailSettings,
    evaluate_proposed_buy_guardrails,
)


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "guardrails.db"


def test_proposed_buy_passes_when_within_limits(db_path):
    service = PaperAccountService(str(db_path))
    service.initialise_account(starting_balance=10000)

    status = evaluate_proposed_buy_guardrails(
        service,
        ticker="AAPL",
        proposed_position_value=1000,
        settings=GuardrailSettings(
            max_total_exposure_pct=80,
            max_open_positions=8,
            daily_loss_limit_pct=3,
            consecutive_loss_limit=3,
        ),
    )

    assert status.allowed
    assert status.projected_exposure_pct == pytest.approx(10)
    assert status.projected_open_positions == 1


def test_proposed_buy_blocks_projected_exposure(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account(starting_balance=10000)

    service.repository.upsert_position(
        account.id,
        "MSFT",
        shares=70,
        average_entry_price=100,
        current_price=100,
    )
    service.repository.update_cash(account.id, 3000)

    status = evaluate_proposed_buy_guardrails(
        service,
        ticker="AAPL",
        proposed_position_value=2000,
        settings=GuardrailSettings(
            max_total_exposure_pct=80,
            max_open_positions=8,
            daily_loss_limit_pct=3,
            consecutive_loss_limit=3,
        ),
    )

    assert not status.allowed
    assert status.projected_exposure_pct == pytest.approx(90)


def test_existing_ticker_does_not_increase_position_count(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account(starting_balance=10000)

    service.repository.upsert_position(
        account.id,
        "AAPL",
        shares=10,
        average_entry_price=100,
        current_price=100,
    )
    service.repository.update_cash(account.id, 9000)

    status = evaluate_proposed_buy_guardrails(
        service,
        ticker="AAPL",
        proposed_position_value=500,
        settings=GuardrailSettings(
            max_total_exposure_pct=80,
            max_open_positions=1,
            daily_loss_limit_pct=3,
            consecutive_loss_limit=3,
        ),
    )

    assert status.projected_open_positions == 1
    assert status.allowed


def test_new_ticker_blocks_when_position_limit_reached(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account(starting_balance=10000)

    service.repository.upsert_position(
        account.id,
        "AAPL",
        shares=10,
        average_entry_price=100,
        current_price=100,
    )
    service.repository.update_cash(account.id, 9000)

    status = evaluate_proposed_buy_guardrails(
        service,
        ticker="MSFT",
        proposed_position_value=500,
        settings=GuardrailSettings(
            max_total_exposure_pct=80,
            max_open_positions=1,
            daily_loss_limit_pct=3,
            consecutive_loss_limit=3,
        ),
    )

    assert not status.allowed
    assert status.projected_open_positions == 2


def test_consecutive_losses_pause_new_buy(db_path):
    service = PaperAccountService(str(db_path))
    service.initialise_account(starting_balance=10000)

    orders = PaperOrderService(
        str(db_path),
        commission=0,
        slippage_pct=0,
    )

    for ticker in ["AAA", "BBB", "CCC"]:
        orders.buy_market(
            ticker=ticker,
            shares=1,
            market_price=100,
        )
        orders.sell_market(
            ticker=ticker,
            shares=1,
            market_price=90,
        )

    status = evaluate_proposed_buy_guardrails(
        service,
        ticker="DDD",
        proposed_position_value=500,
        settings=GuardrailSettings(
            max_total_exposure_pct=80,
            max_open_positions=8,
            daily_loss_limit_pct=50,
            consecutive_loss_limit=3,
        ),
    )

    assert not status.allowed
    assert any("consecutive" in x.lower() for x in status.blockers)
