import pytest
from paper_trading import PaperAccountService, PaperOrderService, build_positions_frame, calculate_portfolio_analytics, get_position_details

@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "portfolio.db"

def seed(db_path):
    svc = PaperAccountService(str(db_path))
    svc.initialise_account(starting_balance=20000)
    orders = PaperOrderService(str(db_path), commission=0, slippage_pct=0)
    orders.buy_market(ticker="AAPL", shares=10, market_price=100, reason="Buy", atlas_score=90, confidence=8)
    orders.buy_market(ticker="MSFT", shares=5, market_price=200, reason="Buy", atlas_score=85, confidence=7)
    svc.update_market_prices({"AAPL":110,"MSFT":180})
    return svc

def test_positions_frame_allocations(db_path):
    frame = build_positions_frame(seed(db_path))
    assert len(frame) == 2
    assert frame["Allocation"].sum() == pytest.approx(1.0)

def test_winners_and_losers(db_path):
    a = calculate_portfolio_analytics(seed(db_path))
    assert a.winning_positions == 1
    assert a.losing_positions == 1
    assert a.largest_winner_ticker == "AAPL"
    assert a.largest_loser_ticker == "MSFT"

def test_equity_marked_to_market(db_path):
    a = calculate_portfolio_analytics(seed(db_path))
    assert a.invested_value == pytest.approx(2000)
    assert a.unrealised_pnl == pytest.approx(0)
    assert a.equity == pytest.approx(20000)

def test_position_details_context(db_path):
    d = get_position_details(seed(db_path), "AAPL")
    assert d["latest_journal"]["atlas_score"] == 90
    assert d["latest_journal"]["confidence"] == 8
    assert d["latest_order"]["side"] == "BUY"

def test_scores_bounded(db_path):
    a = calculate_portfolio_analytics(seed(db_path))
    assert 0 <= a.diversification_score <= 100
    assert 0 <= a.concentration_score <= 100

def test_empty_portfolio_safe(db_path):
    svc = PaperAccountService(str(db_path))
    svc.initialise_account(starting_balance=5000)
    a = calculate_portfolio_analytics(svc)
    assert build_positions_frame(svc).empty
    assert a.equity == 5000
    assert a.open_positions == 0
