"""Cohort validation for prospective Atlas forward tests."""

from __future__ import annotations
import pandas as pd


def _score_band(value):
    if pd.isna(value): return "Unknown"
    value=float(value)
    if value >= 80: return "80–100"
    if value >= 60: return "60–79"
    if value >= 40: return "40–59"
    return "0–39"


def _confidence_band(value):
    if pd.isna(value): return "Unknown"
    value=float(value)
    if value >= 8: return "High (8–10)"
    if value >= 5: return "Medium (5–7.9)"
    return "Low (<5)"


def prepare_cohorts(frame):
    if frame is None or frame.empty:
        return pd.DataFrame()
    d=frame.copy()
    d["return_pct"]=pd.to_numeric(d["return_pct"],errors="coerce")
    d["excess_return_pct"]=pd.to_numeric(
        d.get("excess_return_pct"),errors="coerce")
    d["atlas_score"]=pd.to_numeric(d.get("atlas_score"),errors="coerce")
    d["confidence"]=pd.to_numeric(d.get("confidence"),errors="coerce")
    d["Score Band"]=d["atlas_score"].map(_score_band)
    d["Confidence Band"]=d["confidence"].map(_confidence_band)
    return d.dropna(subset=["return_pct"])


def cohort_table(frame, dimension, minimum_observations=5):
    d=prepare_cohorts(frame)
    if d.empty or dimension not in d.columns:
        return pd.DataFrame()

    rows=[]
    for (cohort,horizon),g in d.groupby([dimension,"horizon_days"],dropna=False):
        benchmark=g.dropna(subset=["excess_return_pct"])
        taken=g[g["decision"].astype(str).str.upper()=="TAKEN"]
        skipped=g[g["decision"].astype(str).str.upper()=="SKIPPED"]
        edge=None
        if not taken.empty and not skipped.empty:
            edge=float(taken["return_pct"].mean()-skipped["return_pct"].mean())
        rows.append({
            dimension:str(cohort),
            "Horizon Days":int(horizon),
            "Observations":len(g),
            "Taken":len(taken),
            "Skipped":len(skipped),
            "Average Return":float(g["return_pct"].mean()),
            "Positive Rate":float((g["return_pct"]>0).mean()),
            "Avg Excess Return":(
                float(benchmark["excess_return_pct"].mean())
                if not benchmark.empty else None),
            "Beat Benchmark Rate":(
                float((benchmark["excess_return_pct"]>0).mean())
                if not benchmark.empty else None),
            "Decision Edge":edge,
            "Evidence Ready":len(g)>=minimum_observations,
        })
    return pd.DataFrame(rows).sort_values(
        ["Horizon Days","Observations"],ascending=[True,False]
    ).reset_index(drop=True)


def score_band_validation(frame, minimum_observations=5):
    return cohort_table(
        frame,"Score Band",minimum_observations=minimum_observations)


def confidence_validation(frame, minimum_observations=5):
    return cohort_table(
        frame,"Confidence Band",minimum_observations=minimum_observations)


def decision_cohort_validation(frame, minimum_observations=5):
    return cohort_table(
        frame,"decision",minimum_observations=minimum_observations)


def strongest_cohort(table, dimension):
    if table is None or table.empty:
        return None
    ready=table[table["Evidence Ready"]==True].copy()
    ready=ready.dropna(subset=["Avg Excess Return"])
    if ready.empty:
        return None
    best=ready.sort_values(
        ["Avg Excess Return","Observations"],ascending=[False,False]
    ).iloc[0]
    return {
        "dimension":dimension,
        "cohort":best[dimension],
        "horizon_days":int(best["Horizon Days"]),
        "observations":int(best["Observations"]),
        "avg_excess_return":float(best["Avg Excess Return"]),
        "positive_rate":float(best["Positive Rate"]),
    }


def score_monotonicity(frame, horizon_days):
    """Does higher Atlas Score correspond to higher realised returns?"""
    d=prepare_cohorts(frame)
    if d.empty:return None
    d=d[d["horizon_days"]==int(horizon_days)].dropna(
        subset=["atlas_score","return_pct"])
    if len(d)<5 or d["atlas_score"].nunique()<2:
        return None
    return float(d["atlas_score"].corr(d["return_pct"]))

def market_regime_validation(frame, minimum_observations=5):
    return cohort_table(frame,"market_regime",minimum_observations=minimum_observations)

def volatility_regime_validation(frame, minimum_observations=5):
    return cohort_table(frame,"volatility_regime",minimum_observations=minimum_observations)
