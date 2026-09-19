"""Sprint 34.3: evidence-aware Atlas Score / strategy analytics.

Uses exact paper_trade_entry_links -> BUY order lineage and the intelligence snapshot
captured at entry time. This avoids judging a completed trade with later scanner data.
"""
from __future__ import annotations
import pandas as pd
from .database import PaperTradingDatabase
from .intelligence_snapshot import SCHEMA as INTELLIGENCE_SCHEMA

SCORE_BINS=[0,60,70,80,90,101]
SCORE_LABELS=["<60","60-69","70-79","80-89","90+"]

def build_entry_intelligence_outcomes(db_path="data/paper_trading.db", account_id=None):
    db=PaperTradingDatabase(db_path)
    with db.connect() as c:
        c.executescript(INTELLIGENCE_SCHEMA)
        params=[]
        where=""
        if account_id is not None:
            where="WHERE t.account_id=?"
            params=[int(account_id)]
        f=pd.read_sql_query(f"""
            SELECT t.id AS trade_id,t.account_id,t.ticker,t.realised_pnl,t.return_pct,
                   l.buy_order_id,l.allocation_weight,
                   s.atlas_score,s.confidence,s.historical_verdict,
                   s.trend_regime,s.volatility_regime,s.evidence_level,s.sample_grade
            FROM paper_trades t
            JOIN paper_trade_entry_links l ON l.trade_id=t.id
            LEFT JOIN paper_intelligence_snapshots s ON s.order_id=l.buy_order_id
            {where}
            ORDER BY t.id,l.buy_order_id
        """,c,params=params)
    if f.empty: return f
    for col in ["realised_pnl","return_pct","allocation_weight","atlas_score","confidence"]:
        f[col]=pd.to_numeric(f[col],errors="coerce")
    # Allocate trade outcome across entry lots so scaled entries do not double count P&L.
    f["allocated_pnl"]=f["realised_pnl"]*f["allocation_weight"]
    return f

def _aggregate(f, group_col, minimum_trades=1):
    if f.empty or group_col not in f: return pd.DataFrame()
    d=f.dropna(subset=[group_col]).copy()
    if d.empty: return pd.DataFrame()
    # A trade can have multiple lots in the same bucket. Collapse to one row per trade/bucket.
    d=d.groupby(["trade_id",group_col],as_index=False,observed=True).agg(
        realised_pnl=("allocated_pnl","sum"), return_pct=("return_pct","mean"))
    g=d.groupby(group_col,as_index=False,observed=True).agg(
        Trades=("trade_id","nunique"),
        Win_Rate=("realised_pnl",lambda s:float((s>0).mean())),
        Average_Return=("return_pct","mean"),
        Net_PnL=("realised_pnl","sum"),
        Expectancy=("realised_pnl","mean"),
    )
    g=g[g.Trades>=int(minimum_trades)].copy()
    return g.sort_values(["Expectancy","Trades"],ascending=[False,False]).reset_index(drop=True)

def performance_by_entry_atlas_score(db_path="data/paper_trading.db",account_id=None,minimum_trades=1):
    f=build_entry_intelligence_outcomes(db_path,account_id)
    if f.empty: return pd.DataFrame()
    f=f.dropna(subset=["atlas_score"]).copy()
    if f.empty: return pd.DataFrame()
    f["Atlas Score Band"]=pd.cut(f.atlas_score,SCORE_BINS,labels=SCORE_LABELS,right=False,include_lowest=True)
    return _aggregate(f,"Atlas Score Band",minimum_trades)

def performance_by_entry_confidence(db_path="data/paper_trading.db",account_id=None,minimum_trades=1):
    return _aggregate(build_entry_intelligence_outcomes(db_path,account_id),"confidence",minimum_trades)

def performance_by_entry_verdict(db_path="data/paper_trading.db",account_id=None,minimum_trades=1):
    f=build_entry_intelligence_outcomes(db_path,account_id)
    if f.empty: return pd.DataFrame()
    f["historical_verdict"]=f["historical_verdict"].fillna("").astype(str).str.strip().replace("","Unknown")
    return _aggregate(f,"historical_verdict",minimum_trades)

def score_monotonicity(score_frame):
    """Describe whether observed average return generally rises with score band.

    Returns None until at least 3 populated bands exist; deliberately descriptive,
    not a trading recommendation.
    """
    if score_frame is None or score_frame.empty or len(score_frame)<3: return None
    order={label:i for i,label in enumerate(SCORE_LABELS)}
    d=score_frame.copy()
    d["_order"]=d["Atlas Score Band"].astype(str).map(order)
    d=d.dropna(subset=["_order","Average_Return"]).sort_values("_order")
    if len(d)<3:return None
    rho=d["_order"].corr(pd.to_numeric(d["Average_Return"],errors="coerce"),method="spearman")
    if pd.isna(rho):return None
    if rho>=0.5:return "Positive relationship"
    if rho<=-0.5:return "Negative relationship"
    return "Mixed relationship"
