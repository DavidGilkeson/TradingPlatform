"""Calibrate Atlas entry intelligence against realised paper outcomes."""

from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .account import PaperAccountService
from .intelligence_snapshot import IntelligenceSnapshotRepository


@dataclass(slots=True)
class CalibrationSummary:
    calibrated_trades:int
    exact_linked_allocations:int
    legacy_unlinked_trades:int
    correlation:float|None
    high_score_win_rate:float|None
    low_score_win_rate:float|None
    score_direction_valid:bool|None


def build_calibration_frame(service:PaperAccountService)->pd.DataFrame:
    """Return exact realised-outcome allocations linked to BUY snapshots.

    Each SELL-created paper trade can link to one or more originating BUY
    orders. Realised P&L is allocated by the share weight recorded at exit.
    Return percentage remains the aggregate realised trade return because the
    established paper-trade engine realises against weighted-average cost.
    """
    IntelligenceSnapshotRepository(str(service.database.db_path))
    account=service.active_account()

    with service.database.connect() as c:
        frame=pd.read_sql_query("""
            SELECT
                t.id AS trade_id,
                t.account_id,
                t.ticker,
                t.entry_date,
                t.exit_date,
                t.shares AS trade_shares,
                t.realised_pnl,
                t.return_pct,
                l.buy_order_id,
                l.allocated_shares,
                l.allocation_weight,
                s.atlas_score,
                s.confidence,
                s.trend_regime,
                s.volatility_regime,
                s.historical_match_score,
                s.matched_trades,
                s.historical_win_rate,
                s.historical_expectancy,
                s.evidence_level,
                s.sample_grade,
                s.reliability,
                s.historical_verdict,
                s.created_at AS snapshot_created_at
            FROM paper_trades t
            JOIN paper_trade_entry_links l
              ON l.trade_id = t.id
            JOIN paper_intelligence_snapshots s
              ON s.order_id = l.buy_order_id
            WHERE t.account_id = ?
            ORDER BY t.exit_date DESC, t.id DESC, l.buy_order_id
        """,c,params=(account.id,))

    if frame.empty:
        return frame

    frame["allocated_realised_pnl"] = (
        pd.to_numeric(frame["realised_pnl"],errors="coerce")
        * pd.to_numeric(frame["allocation_weight"],errors="coerce")
    )
    frame["is_win"] = pd.to_numeric(
        frame["realised_pnl"],errors="coerce"
    ) > 0
    return frame


def calibration_linkage_quality(service:PaperAccountService)->tuple[int,int]:
    """Return exact linked allocation count and legacy unlinked trade count."""
    account=service.active_account()
    with service.database.connect() as c:
        exact=int(c.execute("""
            SELECT COUNT(*)
            FROM paper_trade_entry_links l
            JOIN paper_trades t ON t.id=l.trade_id
            WHERE t.account_id=?
        """,(account.id,)).fetchone()[0])

        legacy=int(c.execute("""
            SELECT COUNT(*)
            FROM paper_trades t
            WHERE t.account_id=?
              AND NOT EXISTS (
                SELECT 1
                FROM paper_trade_entry_links l
                WHERE l.trade_id=t.id
              )
        """,(account.id,)).fetchone()[0])

    return exact,legacy


def _score_band(score)->str:
    score=float(score)
    if score>=80:return "80-100"
    if score>=60:return "60-79"
    if score>=40:return "40-59"
    return "0-39"


def calibration_by_match_score(service:PaperAccountService)->pd.DataFrame:
    frame=build_calibration_frame(service)
    if frame.empty:return pd.DataFrame()

    frame=frame.dropna(subset=["historical_match_score","allocated_realised_pnl"])
    if frame.empty:return pd.DataFrame()

    frame["Match Band"]=frame["historical_match_score"].map(_score_band)

    rows=[]
    for band,group in frame.groupby("Match Band"):
        total_weight=float(group["allocation_weight"].sum())
        win_weight=float(group.loc[group["is_win"],"allocation_weight"].sum())
        weighted_return=(
            float((group["return_pct"]*group["allocation_weight"]).sum()/total_weight)
            if total_weight>0 else 0.0
        )
        rows.append({
            "Match Band":band,
            "Entry Allocations":len(group),
            "Equivalent Trades":total_weight,
            "Win_Rate":win_weight/total_weight if total_weight>0 else 0.0,
            "Average_Return":weighted_return,
            "Net_PnL":float(group["allocated_realised_pnl"].sum()),
            "Expectancy":(
                float(group["allocated_realised_pnl"].sum()/total_weight)
                if total_weight>0 else 0.0
            ),
            "Average_Match":float(
                (group["historical_match_score"]*group["allocation_weight"]).sum()
                / total_weight
            ) if total_weight>0 else 0.0,
            "Average_Reliability":float(
                (group["reliability"]*group["allocation_weight"]).sum()/total_weight
            ) if total_weight>0 else 0.0,
        })

    result=pd.DataFrame(rows)
    order={"80-100":0,"60-79":1,"40-59":2,"0-39":3}
    result["_order"]=result["Match Band"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def calibration_summary(service:PaperAccountService)->CalibrationSummary:
    frame=build_calibration_frame(service)
    exact,legacy=calibration_linkage_quality(service)

    if frame.empty:
        return CalibrationSummary(0,exact,legacy,None,None,None,None)

    clean=frame.dropna(subset=["historical_match_score","return_pct"])
    if clean.empty:
        return CalibrationSummary(0,exact,legacy,None,None,None,None)

    # Use allocation weights so a partial lot contributes proportionally.
    correlation=None
    if len(clean)>=3 and clean["historical_match_score"].nunique()>1:
        # pandas corr is unweighted; retained as a directional diagnostic.
        correlation=float(
            clean["historical_match_score"].corr(clean["return_pct"])
        )

    high=clean[clean["historical_match_score"]>=80]
    low=clean[clean["historical_match_score"]<60]

    def weighted_win_rate(group):
        if group.empty:return None
        total=float(group["allocation_weight"].sum())
        if total<=0:return None
        wins=float(group.loc[group["is_win"],"allocation_weight"].sum())
        return wins/total

    high_wr=weighted_win_rate(high)
    low_wr=weighted_win_rate(low)
    direction=(high_wr>low_wr) if high_wr is not None and low_wr is not None else None

    return CalibrationSummary(
        calibrated_trades=int(clean["trade_id"].nunique()),
        exact_linked_allocations=exact,
        legacy_unlinked_trades=legacy,
        correlation=correlation,
        high_score_win_rate=high_wr,
        low_score_win_rate=low_wr,
        score_direction_valid=direction,
    )
