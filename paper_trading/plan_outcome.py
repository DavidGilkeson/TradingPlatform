"""Compare prospective entry plans with completed paper-trade outcomes."""

from __future__ import annotations
from .database import PaperTradingDatabase
from .trade_plan import PaperTradePlanRepository


def classify_plan_outcome(plan, trade):
    if not plan:
        return "No entry plan"
    exit_price=float(trade["exit_price"])
    stop=float(plan["stop_price"])
    target=float(plan["target_price"])
    pnl=float(trade["realised_pnl"])
    if exit_price >= target:
        return "Target reached/exceeded"
    if exit_price <= stop:
        return "Stop reached/breached"
    if pnl > 0:
        return "Profitable exit inside plan range"
    if pnl < 0:
        return "Losing exit inside plan range"
    return "Break-even exit"


def plan_vs_outcome_metrics(plan, trade):
    if not plan:
        return None
    entry=float(plan["entry_price"])
    return {
        "planned_entry":entry,
        "planned_stop":float(plan["stop_price"]),
        "planned_target":float(plan["target_price"]),
        "planned_reward_risk":plan.get("planned_reward_risk"),
        "actual_exit":float(trade["exit_price"]),
        "actual_return_pct":float(trade["return_pct"]),
        "realised_pnl":float(trade["realised_pnl"]),
        "planned_target_return_pct":round(
            (float(plan["target_price"])/entry-1)*100, 10),
        "planned_stop_return_pct":round(
            (float(plan["stop_price"])/entry-1)*100, 10),
        "outcome":classify_plan_outcome(plan,trade),
    }


class PlanOutcomeRepository:
    def __init__(self,db_path="data/paper_trading.db"):
        self.database=PaperTradingDatabase(db_path)
        self.plans=PaperTradePlanRepository(db_path)

    def entry_plans_for_trade(self,trade_id):
        with self.database.connect() as c:
            links=c.execute("""
                SELECT buy_order_id,allocated_shares,allocation_weight
                FROM paper_trade_entry_links
                WHERE trade_id=?
                ORDER BY allocation_weight DESC,buy_order_id
            """,(int(trade_id),)).fetchall()
        results=[]
        for link in links:
            plan=self.plans.get_by_order(int(link["buy_order_id"]))
            if plan:
                plan=dict(plan)
                plan["allocated_shares"]=float(link["allocated_shares"])
                plan["allocation_weight"]=float(link["allocation_weight"])
                results.append(plan)
        return results

    def primary_plan_for_trade(self,trade_id):
        plans=self.entry_plans_for_trade(trade_id)
        return plans[0] if plans else None

    def trade(self,trade_id):
        with self.database.connect() as c:
            row=c.execute(
                "SELECT * FROM paper_trades WHERE id=?",(int(trade_id),)
            ).fetchone()
        return dict(row) if row else None

    def comparison(self,trade_id):
        trade=self.trade(trade_id)
        if not trade:
            return None
        plans=self.entry_plans_for_trade(trade_id)
        plan=plans[0] if plans else None
        return {
            "trade":trade,
            "plan":plan,
            "metrics":plan_vs_outcome_metrics(plan,trade),
            "all_entry_plans":plans,
        }
