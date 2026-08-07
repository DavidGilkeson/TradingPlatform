from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .account import PaperAccountService

@dataclass(slots=True)
class JournalAnalytics:
    total_trades:int; winning_trades:int; losing_trades:int
    win_rate:float; net_pnl:float; average_winner:float
    average_loser:float; profit_factor:float|None; expectancy:float
    best_trade_ticker:str|None; best_trade_return:float
    worst_trade_ticker:str|None; worst_trade_return:float
    average_entry_atlas_score:float|None; average_confidence:float|None

def build_trade_journal_frame(service: PaperAccountService) -> pd.DataFrame:
    account = service.active_account()
    with service.database.connect() as c:
        trades = pd.read_sql_query("""
            SELECT t.id trade_id,t.ticker,t.entry_date,t.exit_date,t.shares,
                   t.entry_price,t.exit_price,t.realised_pnl,t.return_pct,
                   t.commission,
                   j.reason,j.notes,j.confidence,j.atlas_score
            FROM paper_trades t
            LEFT JOIN paper_journal j
              ON j.account_id=t.account_id AND j.ticker=t.ticker
             AND j.action='SELL'
             AND j.created_at=(
                SELECT MAX(j2.created_at) FROM paper_journal j2
                WHERE j2.account_id=t.account_id AND j2.ticker=t.ticker
                  AND j2.action='SELL' AND j2.created_at<=t.exit_date
             )
            WHERE t.account_id=?
            ORDER BY t.exit_date DESC,t.id DESC
        """, c, params=(account.id,))
    if not trades.empty:
        trades["entry_date"] = pd.to_datetime(trades["entry_date"], errors="coerce")
        trades["exit_date"] = pd.to_datetime(trades["exit_date"], errors="coerce")
        trades["result"] = trades["realised_pnl"].map(
            lambda x: "WIN" if x>0 else "LOSS" if x<0 else "BREAK EVEN"
        )
    return trades

def build_entry_context_frame(service: PaperAccountService) -> pd.DataFrame:
    account = service.active_account()
    with service.database.connect() as c:
        return pd.read_sql_query("""
            SELECT ticker,reason,notes,confidence,atlas_score,created_at
            FROM paper_journal
            WHERE account_id=? AND action='BUY'
            ORDER BY created_at DESC
        """, c, params=(account.id,))

def calculate_journal_analytics(service: PaperAccountService) -> JournalAnalytics:
    trades = build_trade_journal_frame(service)
    entries = build_entry_context_frame(service)
    if trades.empty:
        return JournalAnalytics(0,0,0,0,0,0,0,None,0,None,0,None,0,None,None)

    winners = trades[trades.realised_pnl>0]
    losers = trades[trades.realised_pnl<0]
    total=len(trades); wins=len(winners); losses=len(losers)
    win_rate=wins/total
    gp=float(winners.realised_pnl.sum()) if wins else 0.0
    gl=abs(float(losers.realised_pnl.sum())) if losses else 0.0
    pf=gp/gl if gl>0 else (float("inf") if gp>0 else None)
    aw=float(winners.realised_pnl.mean()) if wins else 0.0
    al=float(losers.realised_pnl.mean()) if losses else 0.0
    expectancy=win_rate*aw+(1-win_rate)*al
    best=trades.loc[trades.return_pct.idxmax()]
    worst=trades.loc[trades.return_pct.idxmin()]

    scores=pd.to_numeric(entries.get("atlas_score"), errors="coerce") if not entries.empty else pd.Series(dtype=float)
    conf=pd.to_numeric(entries.get("confidence"), errors="coerce") if not entries.empty else pd.Series(dtype=float)

    return JournalAnalytics(
        total,wins,losses,win_rate,float(trades.realised_pnl.sum()),aw,al,pf,
        expectancy,str(best.ticker),float(best.return_pct),
        str(worst.ticker),float(worst.return_pct),
        float(scores.mean()) if not scores.dropna().empty else None,
        float(conf.mean()) if not conf.dropna().empty else None
    )

def performance_by_confidence(service):
    f=build_trade_journal_frame(service)
    if f.empty: return pd.DataFrame()
    f["confidence"]=pd.to_numeric(f["confidence"],errors="coerce")
    f=f.dropna(subset=["confidence"])
    if f.empty: return pd.DataFrame()
    return f.groupby("confidence",as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s: float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
    )

def performance_by_atlas_score(service):
    f=build_trade_journal_frame(service)
    if f.empty: return pd.DataFrame()
    f["atlas_score"]=pd.to_numeric(f["atlas_score"],errors="coerce")
    f=f.dropna(subset=["atlas_score"])
    if f.empty: return pd.DataFrame()
    f["Atlas Score Band"]=pd.cut(
        f["atlas_score"], [0,60,70,80,90,101],
        labels=["<60","60-69","70-79","80-89","90+"],
        right=False, include_lowest=True
    )
    return f.groupby("Atlas Score Band",observed=False,as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s: float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
    )
