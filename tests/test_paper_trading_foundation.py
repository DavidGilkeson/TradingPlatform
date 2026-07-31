import pytest
from paper_trading import PaperAccountService, PaperTradingDatabase

@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "paper.db"

def test_tables_created(db_path):
    db = PaperTradingDatabase(db_path)
    with db.connect() as c:
        tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"paper_accounts","paper_positions","paper_orders","paper_trades",
            "paper_journal","paper_account_snapshots"}.issubset(tables)

def test_default_account(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account()
    assert account.cash == 100000
    assert account.buying_power == 100000

def test_initialise_is_idempotent(db_path):
    service = PaperAccountService(str(db_path))
    assert service.initialise_account().id == service.initialise_account().id

def test_snapshot_values_positions(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account(starting_balance=10000)
    service.repository.upsert_position(account.id, "AAPL", 10, 100, 110)
    service.repository.update_cash(account.id, 9000)
    snap = service.snapshot(False)
    assert snap.equity == 10100
    assert snap.unrealised_pnl == 100
    assert snap.total_return_pct == pytest.approx(0.01)

def test_price_update(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account(starting_balance=10000)
    service.repository.upsert_position(account.id, "MSFT", 5, 200, 200)
    service.repository.update_cash(account.id, 9000)
    service.update_market_prices({"msft": 220})
    assert service.snapshot(False).unrealised_pnl == 100

def test_reset_clears_positions(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account()
    service.repository.upsert_position(account.id, "NVDA", 2, 150, 160)
    reset = service.reset_account(starting_balance=50000)
    assert reset.cash == 50000
    assert service.repository.list_positions(reset.id) == []

def test_invalid_balance(db_path):
    service = PaperAccountService(str(db_path))
    with pytest.raises(ValueError):
        service.reset_account(starting_balance=0)

def test_snapshot_persisted(db_path):
    service = PaperAccountService(str(db_path))
    account = service.initialise_account()
    service.snapshot(True)
    assert len(service.repository.list_snapshots(account.id)) == 1
