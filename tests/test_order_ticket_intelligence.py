from paper_trading.intelligence_snapshot import IntelligenceSnapshotRepository
from paper_trading.order_intelligence import derive_regime_from_context

def test_derives_regime_from_scanner_context():
    regime=derive_regime_from_context({
        "Close":110,"20-Day MA":105,"50-Day MA":100,"Volatility (%)":1.2})
    assert regime is not None
    assert regime.trend=="Bullish"
    assert regime.volatility=="Lower Volatility"

def test_missing_mas_returns_none():
    assert derive_regime_from_context({"Close":100}) is None

def test_snapshot_roundtrip(tmp_path):
    repo=IntelligenceSnapshotRepository(str(tmp_path/"snapshot.db"))
    repo.save(order_id=7,account_id=1,ticker="aapl",atlas_score=92,
              confidence=9,trend_regime="Bullish",
              volatility_regime="Lower Volatility",
              historical_match_score=78,matched_trades=14,
              historical_win_rate=.71,historical_expectancy=42.5,
              evidence_level="Moderate",sample_grade="Developing",
              reliability=43,historical_verdict="Historically favourable")
    r=repo.get(7)
    assert r is not None
    assert r.ticker=="AAPL"
    assert r.historical_match_score==78
    assert r.matched_trades==14
    assert r.historical_verdict=="Historically favourable"

def test_snapshot_upsert(tmp_path):
    repo=IntelligenceSnapshotRepository(str(tmp_path/"snapshot.db"))
    repo.save(order_id=1,account_id=1,ticker="AAPL",historical_match_score=50)
    repo.save(order_id=1,account_id=1,ticker="AAPL",historical_match_score=70)
    assert repo.get(1).historical_match_score==70
