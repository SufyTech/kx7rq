from pathlib import Path

import pandas as pd

UTC = "UTC"
DATA = Path(__file__).resolve().parents[1] / "data"


def load(d=DATA):
    act = pd.read_csv(Path(d) / "actual.csv")
    act["startTime"] = pd.to_datetime(act.startTime, utc=True)
    actual = act.set_index("startTime").generation.resample("1h").mean().rename("actual")
    fc = pd.read_csv(Path(d) / "forecast.csv")
    for c in ("startTime", "publishTime"):
        fc[c] = pd.to_datetime(fc[c], utc=True)
    return actual, fc


def latest_before_cutoff(fc, day, cutoff_hour=12, days_before=1):
    """For one delivery day: newest forecast per hour published at or before the cutoff."""
    day = pd.Timestamp(day, tz=UTC)
    cutoff = day - pd.Timedelta(days=days_before) + pd.Timedelta(hours=cutoff_hour)
    t = fc[(fc.startTime >= day) & (fc.startTime < day + pd.Timedelta(days=1))
           & (fc.publishTime <= cutoff)]
    return t.sort_values("publishTime").groupby("startTime").tail(1).set_index("startTime").sort_index()


def backtest(fc, actual, cutoff_hour=12, days_before=1):
    """Every purchase decision made in January 2026 (delivery = decision day + days_before)."""
    decisions = pd.date_range("2026-01-01", "2026-01-31")
    parts = [latest_before_cutoff(fc, d + pd.Timedelta(days=days_before), cutoff_hour, days_before)
             for d in decisions]
    df = pd.concat(parts).join(actual, how="inner")
    if df.empty:
        return df
    df["error"] = df.generation - df.actual
    return df


def metrics(df):
    e = df.error
    return {"n": len(e), "mae": e.abs().mean(), "rmse": (e**2).mean()**0.5,
            "bias": e.mean(), "p90_abs": e.abs().quantile(0.9)}


def by_lead(fc, actual, bin_h=6):
    """Error by forecast age, using forecasts published in January 2026 only."""
    jan = (fc.publishTime >= pd.Timestamp("2026-01-01", tz=UTC)) & (fc.publishTime < pd.Timestamp("2026-02-01", tz=UTC))
    d = fc[jan].join(actual, on="startTime", how="inner")
    d["lead_h"] = (d.startTime - d.publishTime).dt.total_seconds() / 3600
    d = d[d.lead_h >= 0].copy()
    d["err"] = d.generation - d.actual
    d["bucket"] = (d.lead_h // bin_h * bin_h).astype(int)
    return d.groupby("bucket").err.agg(mae=lambda e: e.abs().mean(), bias="mean", n="size").round(0)


if __name__ == "__main__":
    actual, fc = load()
    df = backtest(fc, actual)
    print("hours covered (expect 744):", len(df))
    print({k: round(float(v), 1) for k, v in metrics(df).items()})