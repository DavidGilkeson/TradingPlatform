"""Calibrate Atlas entry-time intelligence against realised paper outcomes."""

from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .account import PaperAccountService


@dataclass(slots=True)
class CalibrationSummary:
    calibrated_trades:int
    correlation:float|None
    high_score_win_rate:float|None
    low_score_win_rate:float|None
    score_direction_valid:bool|None


def build_calibration_frame(service:PaperAccountService)->pd.DataFrame:
    """Match each realised trade to the latest eligible BUY snapshot before entry.

    This uses only snapshots recorded no later than the trade's entry time and
    avoids future information. For positions built with multiple BUYs, the most
    recent snapshot at/before entry is used as the conservative available link
    in the current schema.
    """
    account=service.active_account()
    with service.database.connect() as c:
        trades=pd.read_sql_query("""
            SELECT id trade_id,account_id,ticker,entry_date,exit_date,shares,
                   realised_pnl,return_pct
            FROM paper_trades
            WHERE account_id=?
            ORDER BY exit_date DESC,id DESC
        """,c,params=(account.id,))
        snapshots=pd.read_sql_query("""
            SELECT order_id,account_id,ticker,atlas_score,confidence,
                   trend_regime,volatility_regime,historical_match_score,
                   matched_trades,historical_win_rate,historical_expectancy,
                   evidence_level,sample_grade,reliability,historical_verdict,
                   created_at
            FROM paper_intelligence_snapshots
            WHERE account_id=?
            ORDER BY created_at
        """,c,params=(account.id,))

    if trades.empty or snapshots.empty:
        return pd.DataFrame()

    trades["entry_date"]=pd.to_datetime(trades["entry_date"],utc=True,errors="coerce")
    snapshots["created_at"]=pd.to_datetime(snapshots["created_at"],utc=True,errors="coerce")
    rows=[]
    for _,trade in trades.iterrows():
        eligible=snapshots[
            (snapshots["ticker"].astype(str).str.upper()==str(trade["ticker"]).upper())
            & (snapshots["created_at"]<=trade["entry_date"])
        ]
        if eligible.empty:
            continue
        snap=eligible.sort_values("created_at").iloc[-1]
        row=trade.to_dict()
        for col in snapshots.columns:
            if col not in {"account_id","ticker"}:
                row[col]=snap[col]
        rows.append(row)
    return pd.DataFrame(rows)


def _score_band(score)->str:
    score=float(score)
    if score>=80:return "80-100"
    if score>=60:return "60-79"
    if score>=40:return "40-59"
    return "0-39"


def calibration_by_match_score(service:PaperAccountService)->pd.DataFrame:
    frame=build_calibration_frame(service)
    if frame.empty:return pd.DataFrame()
    frame=frame.dropna(subset=["historical_match_score","realised_pnl"])
    if frame.empty:return pd.DataFrame()
    frame["Match Band"]=frame["historical_match_score"].map(_score_band)
    result=frame.groupby("Match Band",as_index=False).agg(
        Trades=("trade_id","count"),
        Win_Rate=("realised_pnl",lambda s:float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
        Expectancy=("realised_pnl","mean"),
        Average_Match=("historical_match_score","mean"),
        Average_Reliability=("reliability","mean"),
    )
    order={"80-100":0,"60-79":1,"40-59":2,"0-39":3}
    result["_order"]=result["Match Band"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def calibration_summary(service:PaperAccountService)->CalibrationSummary:
    frame=build_calibration_frame(service)
    if frame.empty:
        return CalibrationSummary(0,None,None,None,None)
    frame=frame.dropna(subset=["historical_match_score","realised_pnl"])
    if frame.empty:
        return CalibrationSummary(0,None,None,None,None)

    correlation=None
    if len(frame)>=3 and frame["historical_match_score"].nunique()>1:
        correlation=float(frame["historical_match_score"].corr(frame["return_pct"]))

    high=frame[frame["historical_match_score"]>=80]
    low=frame[frame["historical_match_score"]<60]
    high_wr=float((high["realised_pnl"]>0).mean()) if not high.empty else None
    low_wr=float((low["realised_pnl"]>0).mean()) if not low.empty else None
    direction=(high_wr>low_wr) if high_wr is not None and low_wr is not None else None
    return CalibrationSummary(len(frame),correlation,high_wr,low_wr,direction)
