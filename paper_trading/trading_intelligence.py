from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .account import PaperAccountService
from .journal_analytics import build_trade_journal_frame

@dataclass(slots=True)
class IntelligenceSummary:
    total_trades:int
    best_atlas_score_band:str|None
    best_confidence_level:float|None
    best_ticker:str|None
    best_verdict:str|None
    highest_expectancy_bucket:str|None
    strongest_pattern:str|None

def _frame(service:PaperAccountService)->pd.DataFrame:
    f=build_trade_journal_frame(service)
    if f is None or f.empty: return pd.DataFrame()
    f=f.copy()
    for c in ("realised_pnl","return_pct","atlas_score","confidence"):
        if c in f.columns:
            f[c]=pd.to_numeric(f[c],errors="coerce")
    return f

def performance_by_ticker(service, minimum_trades=1):
    f=_frame(service)
    if f.empty: return pd.DataFrame()
    g=f.groupby("ticker",as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s:float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
        Expectancy=("realised_pnl","mean"))
    return g[g["Trades"]>=minimum_trades].sort_values(
        ["Expectancy","Net_PnL"],ascending=[False,False]).reset_index(drop=True)

def performance_by_confidence(service, minimum_trades=1):
    f=_frame(service)
    if f.empty or "confidence" not in f: return pd.DataFrame()
    f=f.dropna(subset=["confidence"])
    if f.empty: return pd.DataFrame()
    g=f.groupby("confidence",as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s:float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
        Expectancy=("realised_pnl","mean"))
    return g[g["Trades"]>=minimum_trades].sort_values(
        ["Expectancy","Win_Rate"],ascending=[False,False]).reset_index(drop=True)

def performance_by_atlas_score(service, minimum_trades=1):
    f=_frame(service)
    if f.empty or "atlas_score" not in f: return pd.DataFrame()
    f=f.dropna(subset=["atlas_score"])
    if f.empty: return pd.DataFrame()
    f["Atlas Score Band"]=pd.cut(
        f["atlas_score"],[0,60,70,80,90,101],
        labels=["<60","60-69","70-79","80-89","90+"],
        right=False,include_lowest=True)
    g=f.groupby("Atlas Score Band",observed=False,as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s:float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
        Expectancy=("realised_pnl","mean"))
    return g[g["Trades"]>=minimum_trades].sort_values(
        ["Expectancy","Win_Rate"],ascending=[False,False]).reset_index(drop=True)

def performance_by_verdict(service, minimum_trades=1):
    f=_frame(service)
    if f.empty or "reason" not in f: return pd.DataFrame()
    f=f.copy()
    f["Verdict"]=f["reason"].fillna("Unknown").astype(str).str.strip().replace("","Unknown")
    g=f.groupby("Verdict",as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s:float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
        Expectancy=("realised_pnl","mean"))
    return g[g["Trades"]>=minimum_trades].sort_values(
        ["Expectancy","Net_PnL"],ascending=[False,False]).reset_index(drop=True)

def derive_intelligence_summary(service, minimum_trades=1):
    trades=_frame(service)
    if trades.empty:
        return IntelligenceSummary(0,None,None,None,None,None,None)
    score=performance_by_atlas_score(service,minimum_trades)
    confidence=performance_by_confidence(service,minimum_trades)
    ticker=performance_by_ticker(service,minimum_trades)
    verdict=performance_by_verdict(service,minimum_trades)

    best_score=str(score.iloc[0]["Atlas Score Band"]) if not score.empty else None
    best_conf=float(confidence.iloc[0]["confidence"]) if not confidence.empty else None
    best_ticker=str(ticker.iloc[0]["ticker"]) if not ticker.empty else None
    best_verdict=str(verdict.iloc[0]["Verdict"]) if not verdict.empty else None

    candidates=[]
    if not score.empty: candidates.append((f"Atlas Score {score.iloc[0]['Atlas Score Band']}",float(score.iloc[0]["Expectancy"])))
    if not confidence.empty: candidates.append((f"Confidence {confidence.iloc[0]['confidence']:.0f}/10",float(confidence.iloc[0]["Expectancy"])))
    if not ticker.empty: candidates.append((f"Ticker {ticker.iloc[0]['ticker']}",float(ticker.iloc[0]["Expectancy"])))
    if not verdict.empty: candidates.append((f"Verdict {verdict.iloc[0]['Verdict']}",float(verdict.iloc[0]["Expectancy"])))

    highest=None; strongest=None
    if candidates:
        candidates.sort(key=lambda x:x[1],reverse=True)
        highest=candidates[0][0]
        strongest=f"{candidates[0][0]} currently has the highest observed paper-trade expectancy (${candidates[0][1]:,.2f} per trade)."

    return IntelligenceSummary(len(trades),best_score,best_conf,best_ticker,best_verdict,highest,strongest)
