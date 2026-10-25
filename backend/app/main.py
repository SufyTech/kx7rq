from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    from analysis import load, latest_before_cutoff, backtest, metrics, by_lead
except ImportError:  # loaded as a package (e.g. on Vercel)
    from app.analysis import load, latest_before_cutoff, backtest, metrics, by_lead

actual, fc = load()
app = FastAPI(title="Wind forecast API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

CUT = Query(12, ge=0, le=23, description="Decision hour (UTC)")
BEFORE = Query(1, ge=0, le=3, description="Days between decision and delivery")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/forecast")
def forecast(decision_date: date = date(2026, 1, 9), cutoff_hour: int = CUT, days_before: int = BEFORE):
    if not date(2026, 1, 1) <= decision_date <= date(2026, 1, 31):
        raise HTTPException(422, "decision_date must be within January 2026")
    delivery = decision_date + timedelta(days=days_before)
    d = latest_before_cutoff(fc, delivery, cutoff_hour, days_before).join(actual, how="left")
    pts = [{"time": t.isoformat(), "forecast": round(float(r.generation)),
            "actual": None if pd.isna(r.actual) else round(float(r.actual)),
            "published": r.publishTime.isoformat()} for t, r in d.iterrows()]
    return {"decision_time": f"{decision_date}T{cutoff_hour:02d}:00:00Z",
            "delivery_day": str(delivery), "points": pts}


@app.get("/api/accuracy")
def accuracy(cutoff_hour: int = CUT, days_before: int = BEFORE):
    df = backtest(fc, actual, cutoff_hour, days_before)
    if df.empty:
        raise HTTPException(404, "No forecasts available for this cutoff")
    return {k: round(float(v)) for k, v in metrics(df).items()}


@app.get("/api/horizon")
def horizon():
    rows = by_lead(fc, actual).reset_index().to_dict("records")
    return [r for r in rows if r["n"] >= 100]


# Docker image: serve the built React app from the same server (folder is absent on Vercel)
STATIC = Path(__file__).resolve().parents[1] / "static"
if STATIC.is_dir():
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="web")