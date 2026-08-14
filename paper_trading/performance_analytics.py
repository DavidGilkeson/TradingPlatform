from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from .journal_analytics import build_trade_journal_frame

@dataclass(slots=True)
class PerformanceSummary:
    starting_balance: float
    current_equity: float
    total_return: float
    net_profit: float
    realised_pnl: float
    unrealised_pnl: float
    max_drawdown: float
    win_rate: float
    profit_factor: float | None
    expectancy: float
    average_trade_return: float
    best_trade_return: float
    worst_trade_return: float
    current_win_streak: int
    current_loss_streak: int
    longest_win_streak: int
    longest_loss_streak: int

def build_equity_history(service):
    account = service.active_account()
    rows = service.repository.list_snapshots(account.id)
    if not rows:
        return pd.DataFrame()
    f = pd.DataFrame(rows)
    f["captured_at"] = pd.to_datetime(f["captured_at"], errors="coerce", utc=True)
    f = f.dropna(subset=["captured_at","equity"]).sort_values("captured_at").drop_duplicates("captured_at")
    for c in ["cash","positions_value","equity","unrealised_pnl","realised_pnl"]:
        f[c] = pd.to_numeric(f[c], errors="coerce").fillna(0.0)
    f["peak_equity"] = f["equity"].cummax()
    f["drawdown"] = f["equity"] - f["peak_equity"]
    f["drawdown_pct"] = (f["equity"]/f["peak_equity"]-1).fillna(0)
    f["cumulative_return"] = f["equity"]/float(account.starting_balance)-1
    return f.reset_index(drop=True)

def _streaks(trades):
    if trades.empty: return 0,0,0,0
    outcomes=[1 if x>0 else -1 if x<0 else 0 for x in pd.to_numeric(trades.sort_values("exit_date")["realised_pnl"],errors="coerce").fillna(0)]
    cur=typ=lw=ll=0
    for o in outcomes:
        if o==0: cur=typ=0; continue
        if o==typ: cur+=1
        else: typ=o; cur=1
        if o==1: lw=max(lw,cur)
        else: ll=max(ll,cur)
    return (cur if typ==1 else 0, cur if typ==-1 else 0, lw, ll)

def calculate_performance_summary(service):
    account=service.active_account()
    snap=service.snapshot(persist=False)
    trades=build_trade_journal_frame(service)
    hist=build_equity_history(service)
    mdd=float(hist["drawdown_pct"].min()) if not hist.empty else 0.0
    if trades.empty:
        wr=0; pf=None; exp=avg=best=worst=0.0
    else:
        pnl=pd.to_numeric(trades["realised_pnl"],errors="coerce").fillna(0)
        ret=pd.to_numeric(trades["return_pct"],errors="coerce").fillna(0)
        winners=pnl[pnl>0]; losers=pnl[pnl<0]
        wr=float((pnl>0).mean())
        gp=float(winners.sum()) if not winners.empty else 0.0
        gl=abs(float(losers.sum())) if not losers.empty else 0.0
        pf=gp/gl if gl>0 else (float("inf") if gp>0 else None)
        aw=float(winners.mean()) if not winners.empty else 0.0
        al=float(losers.mean()) if not losers.empty else 0.0
        exp=wr*aw+(1-wr)*al
        avg=float(ret.mean()); best=float(ret.max()); worst=float(ret.min())
    cw,cl,lw,ll=_streaks(trades)
    return PerformanceSummary(
        float(account.starting_balance), float(snap.equity), float(snap.total_return_pct),
        float(snap.equity-account.starting_balance), float(snap.realised_pnl), float(snap.unrealised_pnl),
        mdd, wr, pf, exp, avg, best, worst, cw, cl, lw, ll
    )

def daily_performance(service):
    f=build_equity_history(service)
    if f.empty: return pd.DataFrame()
    f=f.copy(); f["date"]=f["captured_at"].dt.date
    d=f.groupby("date",as_index=False).tail(1).sort_values("captured_at").reset_index(drop=True)
    d["daily_pnl"]=d["equity"].diff().fillna(0)
    d["daily_return"]=d["equity"].pct_change().fillna(0)
    return d

def rolling_performance(service, window=5):
    if window<=1: raise ValueError("Rolling window must be greater than one.")
    d=daily_performance(service)
    if d.empty: return pd.DataFrame()
    d=d.copy()
    d["rolling_return"]=d["equity"]/d["equity"].shift(window)-1
    d["rolling_volatility"]=d["daily_return"].rolling(window).std()*math.sqrt(252)
    return d

def monthly_performance(service):
    d=daily_performance(service)
    if d.empty: return pd.DataFrame()
    d=d.copy(); d["month"]=d["captured_at"].dt.tz_localize(None).dt.to_period("M").astype(str)
    rows=[]
    for month,g in d.groupby("month",sort=True):
        s=float(g["equity"].iloc[0]); e=float(g["equity"].iloc[-1])
        rows.append({"Month":month,"Starting Equity":s,"Ending Equity":e,"P&L":e-s,"Return":e/s-1 if s else 0})
    return pd.DataFrame(rows)
