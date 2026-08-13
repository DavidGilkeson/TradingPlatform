import pytest
from paper_trading import PaperAccountService, PaperOrderService


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path/"linkage.db"


def test_buy_creates_position_lot(db_path):
    account=PaperAccountService(str(db_path))
    account.initialise_account(starting_balance=10000)
    orders=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    buy=orders.buy_market(ticker="AAPL",shares=10,market_price=100)

    with account.database.connect() as c:
        row=c.execute(
            "SELECT * FROM paper_position_lots WHERE buy_order_id=?",
            (buy.order_id,)).fetchone()

    assert row is not None
    assert row["shares_remaining"]==pytest.approx(10)


def test_partial_sell_links_to_exact_buy_order(db_path):
    account=PaperAccountService(str(db_path))
    account.initialise_account(starting_balance=10000)
    orders=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    buy=orders.buy_market(ticker="AAPL",shares=10,market_price=100)
    orders.sell_market(ticker="AAPL",shares=4,market_price=110)

    with account.database.connect() as c:
        link=c.execute(
            "SELECT * FROM paper_trade_entry_links"
        ).fetchone()
        lot=c.execute(
            "SELECT shares_remaining FROM paper_position_lots WHERE buy_order_id=?",
            (buy.order_id,)).fetchone()

    assert link is not None
    assert link["buy_order_id"]==buy.order_id
    assert link["allocated_shares"]==pytest.approx(4)
    assert link["allocation_weight"]==pytest.approx(1)
    assert lot["shares_remaining"]==pytest.approx(6)


def test_fifo_multiple_buys_create_multiple_links(db_path):
    account=PaperAccountService(str(db_path))
    account.initialise_account(starting_balance=20000)
    orders=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    first=orders.buy_market(ticker="AAPL",shares=5,market_price=100)
    second=orders.buy_market(ticker="AAPL",shares=5,market_price=110)
    orders.sell_market(ticker="AAPL",shares=8,market_price=120)

    with account.database.connect() as c:
        links=c.execute(
            "SELECT * FROM paper_trade_entry_links ORDER BY buy_order_id"
        ).fetchall()

    assert len(links)==2
    assert links[0]["buy_order_id"]==first.order_id
    assert links[0]["allocated_shares"]==pytest.approx(5)
    assert links[1]["buy_order_id"]==second.order_id
    assert links[1]["allocated_shares"]==pytest.approx(3)
    assert sum(row["allocation_weight"] for row in links)==pytest.approx(1)


def test_legacy_position_without_lot_remains_sellable(db_path):
    account=PaperAccountService(str(db_path))
    a=account.initialise_account(starting_balance=10000)
    account.repository.upsert_position(
        a.id,"LEGACY",shares=2,average_entry_price=100,current_price=100
    )
    account.repository.update_cash(a.id,9800)

    orders=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    result=orders.sell_market(ticker="LEGACY",shares=2,market_price=110)
    assert result.realised_pnl==pytest.approx(20)

    with account.database.connect() as c:
        count=c.execute("SELECT COUNT(*) FROM paper_trade_entry_links").fetchone()[0]
    assert count==0
