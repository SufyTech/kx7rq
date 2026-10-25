from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from analysis import load, latest_before_cutoff, backtest, metrics, by_lead

actual, fc = load(str(Path(__file__).resolve().parents[2] / "data"))
app = FastAPI(title="Wind forecast API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

CUT = Query(12, ge=0, le=23, description="Decision hour (UTC)")
BEFORE = Query(1, ge=0, le=3, description="Days before delivery")

@app.get("/api/forecast")
def forecast(day: str = "2026-01-10", cutoff_hour: int = CUT, days_before: int = BEFORE):
    try:
        f = latest_before_cutoff(fc, day, cutoff_hour, days_before)
    except ValueError:
        raise HTTPException(422, "day must be a valid date like 2026-01-10")
    d = f.join(actual, how="left")
    return [{"time": t.isoformat(), "forecast": round(float(r.generation)),
             "actual": None if pd.isna(r.actual) else round(float(r.actual)),
             "published": r.publishTime.isoformat()} for t, r in d.iterrows()]

@app.get("/api/accuracy")
def accuracy(cutoff_hour: int = CUT, days_before: int = BEFORE):
    df = backtest(fc, actual, cutoff_hour=cutoff_hour, days_before=days_before)
    if df.empty:
        raise HTTPException(404, "No forecasts available for this cutoff")
    return {k: round(float(v)) for k, v in metrics(df).items()}

@app.get("/api/horizon")
def horizon():
    rows = by_lead(fc, actual).reset_index().to_dict("records")
    return [r for r in rows if r["n"] >= 100]