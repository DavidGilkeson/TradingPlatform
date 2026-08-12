import pytest
from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.auto_exits import AutomaticExitService
from paper_trading.exit_audit import ExitAuditRepository
from paper_trading.exit_plans import ExitPlanRepository

@pytest.fixture()
def db_path(tmp_path): return tmp_path/"audit.db"

def setup(db_path, price):
    a=PaperAccountService(str(db_path)); a.initialise_account(starting_balance=10000)
    o=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    o.buy_market(ticker="AAPL",shares=10,market_price=100)
    account=a.active_account()
    ExitPlanRepository(str(db_path)).save_plan(account_id=account.id,ticker="AAPL",stop_price=95,target_price=110)
    a.update_market_prices({"AAPL":price})
    return a,account

def test_monitor_records_trigger(db_path):
    a,account=setup(db_path,94)
    events=AutomaticExitService(str(db_path),commission=0,slippage_pct=0).process_triggered_exits(enabled=False)
    assert events==[]
    assert ExitAuditRepository(str(db_path)).list_records(account_id=account.id)[0].decision=="STOP_LOSS_DETECTED"
    assert len(a.repository.list_positions(account.id))==1

def test_override_prevents_exit(db_path):
    a,account=setup(db_path,94)
    events=AutomaticExitService(str(db_path),commission=0,slippage_pct=0).process_triggered_exits(enabled=True,excluded_tickers={"AAPL"})
    assert events==[]
    assert len(a.repository.list_positions(account.id))==1
    assert ExitAuditRepository(str(db_path)).list_records(account_id=account.id)[0].decision=="MANUAL_OVERRIDE"

def test_execution_audited(db_path):
    _,account=setup(db_path,111)
    events=AutomaticExitService(str(db_path),commission=0,slippage_pct=0).process_triggered_exits(enabled=True)
    assert len(events)==1
    assert ExitAuditRepository(str(db_path)).list_records(account_id=account.id)[0].decision=="TAKE_PROFIT_EXECUTED"

def test_no_trigger_audited(db_path):
    _,account=setup(db_path,103)
    events=AutomaticExitService(str(db_path),commission=0,slippage_pct=0).process_triggered_exits(enabled=True)
    assert events==[]
    assert ExitAuditRepository(str(db_path)).list_records(account_id=account.id)[0].decision=="NO_TRIGGER"
