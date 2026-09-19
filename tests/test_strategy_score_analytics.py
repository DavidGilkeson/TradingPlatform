from paper_trading.account import PaperAccountService
from paper_trading.intelligence_snapshot import IntelligenceSnapshotRepository
from paper_trading.strategy_score_analytics import (
    build_entry_intelligence_outcomes,performance_by_entry_atlas_score,
    performance_by_entry_verdict,score_monotonicity,
)

def _seed(tmp_path):
    db=tmp_path/"paper.db"; s=PaperAccountService(db); a=s.initialise_account("Test",100000)
    rows=[(55,-100,-1,"Weak"),(65,50,.5,"Mixed"),(75,200,2,"Good"),(85,300,3,"Good")]
    with s.database.connect() as c:
        for i,(score,pnl,ret,verdict) in enumerate(rows,1):
            c.execute("INSERT INTO paper_orders(id,account_id,ticker,side,requested_shares,status,created_at) VALUES(?,?,?,?,?,?,?)",(i,a.id,f"T{i}","BUY",1,"FILLED","2026-01-01"))
            c.execute("INSERT INTO paper_trades(id,account_id,ticker,entry_date,exit_date,shares,entry_price,exit_price,realised_pnl,return_pct) VALUES(?,?,?,?,?,?,?,?,?,?)",(i,a.id,f"T{i}","2026-01-01","2026-01-02",1,100,100+ret,pnl,ret))
            c.execute("INSERT INTO paper_trade_entry_links(trade_id,buy_order_id,allocated_shares,allocation_weight) VALUES(?,?,?,?)",(i,i,1,1))
    repo=IntelligenceSnapshotRepository(db)
    for i,(score,pnl,ret,verdict) in enumerate(rows,1):
        repo.save(order_id=i,account_id=a.id,ticker=f"T{i}",atlas_score=score,confidence=5+i,historical_verdict=verdict)
    return db,a.id

def test_exact_entry_intelligence_lineage(tmp_path):
    db,aid=_seed(tmp_path); f=build_entry_intelligence_outcomes(db,aid)
    assert len(f)==4 and set(f.atlas_score)=={55,65,75,85}

def test_score_bands_and_outcomes(tmp_path):
    db,aid=_seed(tmp_path); f=performance_by_entry_atlas_score(db,aid)
    assert set(f['Atlas Score Band'].astype(str))=={'<60','60-69','70-79','80-89'}
    assert float(f.loc[f['Atlas Score Band'].astype(str)=='80-89','Net_PnL'].iloc[0])==300

def test_verdict_groups(tmp_path):
    db,aid=_seed(tmp_path); f=performance_by_entry_verdict(db,aid)
    good=f[f.historical_verdict=='Good'].iloc[0]
    assert int(good.Trades)==2 and float(good.Net_PnL)==500

def test_score_relationship_requires_three_bands(tmp_path):
    db,aid=_seed(tmp_path); f=performance_by_entry_atlas_score(db,aid)
    assert score_monotonicity(f)=='Positive relationship'
    assert score_monotonicity(f.head(2)) is None
