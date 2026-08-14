import sqlite3
from paper_trading.trade_plan import PaperTradePlanRepository,reward_risk


def test_reward_risk():
    assert reward_risk(100,95,110)==2
    assert reward_risk(100,100,110) is None


def test_trade_plan_schema(tmp_path):
    repo=PaperTradePlanRepository(str(tmp_path/"plans.db"))
    with repo.database.connect() as c:
        cols={r["name"] for r in c.execute(
            "PRAGMA table_info(paper_trade_plans)").fetchall()}
    assert {"thesis","invalidation","stop_price","target_price",
            "planned_reward_risk","market_regime"}.issubset(cols)


def test_save_and_read_plan(tmp_path):
    db=str(tmp_path/"plans.db")
    repo=PaperTradePlanRepository(db)
    now="2026-08-14T00:00:00+00:00"
    with repo.database.connect() as c:
        c.execute("""INSERT INTO paper_accounts
          (id,name,starting_balance,cash,is_active,created_at,updated_at)
          VALUES(1,'Test',10000,10000,1,?,?)""",(now,now))
        c.execute("""INSERT INTO paper_orders
          (id,account_id,ticker,side,requested_shares,status,created_at,
           commission,slippage)
          VALUES(1,1,'NVDA','BUY',10,'FILLED',?,0,0)""",(now,))
    repo.save(
        account_id=1,buy_order_id=1,ticker="NVDA",
        thesis="Momentum continuation",invalidation="Close below support",
        entry_price=100,stop_price=95,target_price=110,planned_shares=10,
        risk_pct=1,max_position_pct=20,minimum_reward_risk=2,
        confidence=8,atlas_score=92,market_regime="Bullish",
        volatility_regime="Normal")
    plan=repo.get_by_order(1)
    assert plan["thesis"]=="Momentum continuation"
    assert plan["planned_reward_risk"]==2
    assert plan["atlas_score"]==92
