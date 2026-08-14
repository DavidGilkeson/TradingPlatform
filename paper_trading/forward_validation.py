"""Evidence-aware forward validation for Atlas."""

from __future__ import annotations
from dataclasses import dataclass
import pandas as pd


@dataclass(slots=True)
class ValidationScorecard:
    score:int
    grade:str
    evidence_level:str
    observations:int
    resolved_decisions:int
    horizons_covered:int
    decision_edge:float|None
    avg_excess_return:float|None
    benchmark_beat_rate:float|None
    positive_horizon_rate:float|None
    verdict:str


def _grade(score:int)->str:
    if score>=85:return "A"
    if score>=70:return "B"
    if score>=55:return "C"
    if score>=40:return "D"
    return "Early"


def _evidence_level(observations:int)->str:
    if observations>=100:return "Strong"
    if observations>=50:return "Moderate"
    if observations>=20:return "Developing"
    return "Early"


def _clip(value, low=0.0, high=1.0):
    return max(low,min(high,value))


def build_validation_scorecard(frame:pd.DataFrame)->ValidationScorecard:
    if frame is None or frame.empty:
        return ValidationScorecard(
            0,"Early","Early",0,0,0,None,None,None,None,
            "Not enough forward-test evidence yet."
        )

    d=frame.copy()
    d["return_pct"]=pd.to_numeric(d.get("return_pct"),errors="coerce")
    d["excess_return_pct"]=pd.to_numeric(
        d.get("excess_return_pct"),errors="coerce")
    d=d.dropna(subset=["return_pct"])

    if d.empty:
        return ValidationScorecard(
            0,"Early","Early",0,0,0,None,None,None,None,
            "No resolved forward outcomes yet."
        )

    observations=len(d)
    resolved_decisions=d["forward_test_id"].nunique()
    horizons=d["horizon_days"].nunique()

    taken=d[d["decision"].astype(str).str.upper()=="TAKEN"]
    skipped=d[d["decision"].astype(str).str.upper()=="SKIPPED"]

    decision_edge=None
    if not taken.empty and not skipped.empty:
        decision_edge=float(
            taken["return_pct"].mean()-skipped["return_pct"].mean())

    benchmark=d.dropna(subset=["excess_return_pct"])
    avg_excess=None
    beat_rate=None
    if not benchmark.empty:
        avg_excess=float(benchmark["excess_return_pct"].mean())
        beat_rate=float((benchmark["excess_return_pct"]>0).mean())

    horizon_edges=[]
    for _,g in d.groupby("horizon_days"):
        gt=g[g["decision"].astype(str).str.upper()=="TAKEN"]
        gs=g[g["decision"].astype(str).str.upper()=="SKIPPED"]
        if not gt.empty and not gs.empty:
            horizon_edges.append(
                float(gt["return_pct"].mean()-gs["return_pct"].mean())
            )
    positive_horizon_rate=(
        float(sum(x>0 for x in horizon_edges)/len(horizon_edges))
        if horizon_edges else None
    )

    # Score deliberately weights evidence maturity heavily so tiny samples
    # cannot produce a high validation grade.
    sample_component=_clip(observations/100)*35
    horizon_component=_clip(horizons/5)*15

    edge_component=0.0
    if decision_edge is not None:
        edge_component=_clip((decision_edge+5)/10)*15

    excess_component=0.0
    if avg_excess is not None:
        excess_component=_clip((avg_excess+5)/10)*15

    beat_component=(beat_rate or 0.0)*10
    consistency_component=(positive_horizon_rate or 0.0)*10

    score=round(
        sample_component+horizon_component+edge_component+
        excess_component+beat_component+consistency_component
    )

    evidence=_evidence_level(observations)
    grade=_grade(score)

    if evidence=="Early":
        verdict="Promising signals are provisional; collect more forward observations."
    elif score>=70:
        verdict="Forward evidence is developing positively across multiple validation dimensions."
    elif score>=55:
        verdict="Forward evidence is mixed; continue testing before increasing confidence."
    else:
        verdict="Current forward evidence does not yet validate the selection process strongly."

    return ValidationScorecard(
        score,grade,evidence,observations,resolved_decisions,horizons,
        decision_edge,avg_excess,beat_rate,positive_horizon_rate,verdict
    )


def horizon_validation(frame:pd.DataFrame, minimum_per_group:int=5)->pd.DataFrame:
    if frame is None or frame.empty:return pd.DataFrame()
    d=frame.copy()
    d["return_pct"]=pd.to_numeric(d["return_pct"],errors="coerce")
    d["excess_return_pct"]=pd.to_numeric(
        d.get("excess_return_pct"),errors="coerce")
    d=d.dropna(subset=["return_pct"])
    rows=[]
    for horizon,g in d.groupby("horizon_days"):
        taken=g[g["decision"].astype(str).str.upper()=="TAKEN"]
        skipped=g[g["decision"].astype(str).str.upper()=="SKIPPED"]
        edge=None
        ready=len(taken)>=minimum_per_group and len(skipped)>=minimum_per_group
        if not taken.empty and not skipped.empty:
            edge=float(taken["return_pct"].mean()-skipped["return_pct"].mean())
        benchmark=g.dropna(subset=["excess_return_pct"])
        rows.append({
            "Horizon Days":int(horizon),
            "Taken":len(taken),
            "Skipped":len(skipped),
            "Decision Edge":edge,
            "Avg Excess Return":(
                float(benchmark["excess_return_pct"].mean())
                if not benchmark.empty else None),
            "Beat Benchmark Rate":(
                float((benchmark["excess_return_pct"]>0).mean())
                if not benchmark.empty else None),
            "Evidence Ready":ready,
        })
    return pd.DataFrame(rows).sort_values("Horizon Days").reset_index(drop=True)
