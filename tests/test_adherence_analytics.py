import pandas as pd
from paper_trading.adherence_analytics import adherence_summary,execution_bands


def frame():
    return pd.DataFrame([
        {"trade_id":1,"followed_plan":True,"execution_rating":9,
         "return_pct":6.0,"realised_pnl":60},
        {"trade_id":2,"followed_plan":True,"execution_rating":8,
         "return_pct":2.0,"realised_pnl":20},
        {"trade_id":3,"followed_plan":False,"execution_rating":4,
         "return_pct":-3.0,"realised_pnl":-30},
        {"trade_id":4,"followed_plan":False,"execution_rating":3,
         "return_pct":1.0,"realised_pnl":10},
    ])


def test_adherence_summary():
    s=adherence_summary(frame())
    assert s["reviewed_trades"]==4
    assert s["plan_follow_rate"]==0.5
    assert s["average_execution_rating"]==6
    assert s["followed_avg_return"]==4
    assert s["not_followed_avg_return"]==-1
    assert s["followed_net_pnl"]==80
    assert s["not_followed_net_pnl"]==-20


def test_execution_bands():
    bands=execution_bands(frame())
    assert set(bands["Execution Band"].astype(str))=={
        "Low (1–4)","High (8–10)"}
    high=bands[bands["Execution Band"].astype(str)=="High (8–10)"].iloc[0]
    assert high["Trades"]==2
    assert high["Average Return"]==4
    assert high["Win Rate"]==1


def test_empty_summary_safe():
    s=adherence_summary(pd.DataFrame())
    assert s["reviewed_trades"]==0
    assert s["plan_follow_rate"] is None


def test_unreviewed_follow_plan_excluded():
    d=frame()
    d.loc[0,"followed_plan"]=None
    s=adherence_summary(d)
    assert s["reviewed_trades"]==3
