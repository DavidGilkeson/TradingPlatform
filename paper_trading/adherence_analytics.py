"""Analytics for trading-plan adherence and execution discipline."""

from __future__ import annotations
import pandas as pd
from .database import PaperTradingDatabase


def build_adherence_frame(db_path="data/paper_trading.db", account_id=None):
    db=PaperTradingDatabase(db_path)
    where="WHERE t.account_id=?" if account_id is not None else ""
    params=(int(account_id),) if account_id is not None else ()
    with db.connect() as c:
        frame=pd.read_sql_query(f"""
            SELECT
                t.id AS trade_id,t.ticker,t.realised_pnl,t.return_pct,
                r.followed_plan,r.execution_rating,
                r.emotional_state,r.lesson_learned,r.next_time_action
            FROM paper_trades t
            JOIN paper_trade_reviews r ON r.trade_id=t.id
            {where}
            ORDER BY t.exit_date DESC,t.id DESC
        """,c,params=params)
    if frame.empty:
        return frame
    frame["followed_plan"]=frame["followed_plan"].map(
        lambda x: None if pd.isna(x) else bool(x))
    frame["execution_rating"]=pd.to_numeric(
        frame["execution_rating"],errors="coerce")
    frame["realised_pnl"]=pd.to_numeric(frame["realised_pnl"],errors="coerce")
    frame["return_pct"]=pd.to_numeric(frame["return_pct"],errors="coerce")
    return frame


def adherence_summary(frame):
    if frame is None or frame.empty:
        return {
            "reviewed_trades":0,"plan_follow_rate":None,
            "average_execution_rating":None,
            "followed_avg_return":None,"not_followed_avg_return":None,
            "followed_net_pnl":0.0,"not_followed_net_pnl":0.0,
        }
    reviewed=frame[frame["followed_plan"].notna()].copy()
    followed=reviewed[reviewed["followed_plan"]==True]
    missed=reviewed[reviewed["followed_plan"]==False]
    def mean_or_none(series):
        values=pd.to_numeric(series,errors="coerce").dropna()
        return None if values.empty else float(values.mean())
    ratings=pd.to_numeric(frame["execution_rating"],errors="coerce").dropna()
    return {
        "reviewed_trades":len(reviewed),
        "plan_follow_rate":(
            None if reviewed.empty
            else float((reviewed["followed_plan"]==True).mean())
        ),
        "average_execution_rating":(
            None if ratings.empty else float(ratings.mean())
        ),
        "followed_avg_return":mean_or_none(followed["return_pct"]),
        "not_followed_avg_return":mean_or_none(missed["return_pct"]),
        "followed_net_pnl":float(followed["realised_pnl"].sum()),
        "not_followed_net_pnl":float(missed["realised_pnl"].sum()),
    }


def execution_bands(frame):
    if frame is None or frame.empty:
        return pd.DataFrame()
    d=frame.dropna(subset=["execution_rating"]).copy()
    if d.empty:
        return pd.DataFrame()
    d["Execution Band"]=pd.cut(
        d["execution_rating"],
        bins=[0,4,7,10],
        labels=["Low (1–4)","Solid (5–7)","High (8–10)"],
        include_lowest=True,
    )
    return (
        d.groupby("Execution Band",observed=True)
        .agg(
            Trades=("trade_id","count"),
            Average_Return=("return_pct","mean"),
            Net_PnL=("realised_pnl","sum"),
            Win_Rate=("realised_pnl",lambda x: float((x>0).mean())),
        )
        .reset_index()
        .rename(columns={
            "Average_Return":"Average Return",
            "Net_PnL":"Net P&L",
            "Win_Rate":"Win Rate",
        })
    )
