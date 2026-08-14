from paper_trading.plan_outcome import (
    classify_plan_outcome,plan_vs_outcome_metrics,PlanOutcomeRepository)

PLAN={"entry_price":100,"stop_price":95,"target_price":110,
      "planned_reward_risk":2.0}

def test_target_outcome():
    assert classify_plan_outcome(
        PLAN,{"exit_price":111,"realised_pnl":110,"return_pct":11}
    )=="Target reached/exceeded"

def test_stop_outcome():
    assert classify_plan_outcome(
        PLAN,{"exit_price":94,"realised_pnl":-60,"return_pct":-6}
    )=="Stop reached/breached"

def test_inside_range_profit():
    assert classify_plan_outcome(
        PLAN,{"exit_price":105,"realised_pnl":50,"return_pct":5}
    )=="Profitable exit inside plan range"

def test_metrics_preserve_planned_and_actual():
    m=plan_vs_outcome_metrics(
        PLAN,{"exit_price":105,"realised_pnl":50,"return_pct":5})
    assert m["planned_target_return_pct"]==10
    assert m["planned_stop_return_pct"]==-5
    assert m["actual_return_pct"]==5

def test_repository_links_trade_to_buy_plan(tmp_path):
    db=str(tmp_path/"comparison.db")
    repo=PlanOutcomeRepository(db)
    now="2026-08-14T00:00:00+00:00"
    with repo.database.connect() as c:
        c.execute("""INSERT INTO paper_accounts
          (id,name,starting_balance,cash,is_active,created_at,updated_at)
          VALUES(1,'Test',10000,10000,1,?,?)""",(now,now))
        c.execute("""INSERT INTO paper_orders
          (id,account_id,ticker,side,requested_shares,status,created_at,
           commission,slippage)
          VALUES(1,1,'NVDA','BUY',10,'FILLED',?,0,0)""",(now,))
        c.execute("""INSERT INTO paper_trades
          (id,account_id,ticker,entry_date,exit_date,shares,entry_price,
           exit_price,realised_pnl,return_pct,commission)
          VALUES(1,1,'NVDA',?,?,10,100,108,80,8,0)""",(now,now))
        c.execute("""INSERT INTO paper_trade_entry_links
          (trade_id,buy_order_id,allocated_shares,allocation_weight)
          VALUES(1,1,10,1)""")
    repo.plans.save(
        account_id=1,buy_order_id=1,ticker="NVDA",thesis="Breakout",
        invalidation="Below support",entry_price=100,stop_price=95,
        target_price=110,planned_shares=10)
    result=repo.comparison(1)
    assert result["plan"]["thesis"]=="Breakout"
    assert result["metrics"]["actual_exit"]==108
    assert result["metrics"]["outcome"]=="Profitable exit inside plan range"
