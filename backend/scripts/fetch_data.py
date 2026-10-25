import os, requests, pandas as pd
from datetime import datetime, timedelta

B = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

def get(name, **p):
    r = requests.get(f"{B}/{name}/stream", params=p, timeout=120)
    r.raise_for_status()
    d = r.json()
    return d["data"] if isinstance(d, dict) else d

def days(start, end, step):
    while start < end:
        yield start, min(start + timedelta(days=step), end)
        start += timedelta(days=step)

os.makedirs("data", exist_ok=True)

act = []
for a, b in days(datetime(2026, 1, 1), datetime(2026, 2, 1), 5):
    act += get("FUELHH", settlementDateFrom=a.strftime("%Y-%m-%d"),
               settlementDateTo=(b - timedelta(days=1)).strftime("%Y-%m-%d"),
               fuelType="WIND")
act = pd.DataFrame(act).drop_duplicates(["startTime"]).sort_values("startTime")
act.to_csv("data/actual.csv", index=False)

fc = []
for a, b in days(datetime(2025, 12, 25), datetime(2026, 2, 1), 2):
    fc += get("WINDFOR", publishDateTimeFrom=a.strftime("%Y-%m-%dT%H:%MZ"),
              publishDateTimeTo=b.strftime("%Y-%m-%dT%H:%MZ"))
fc = pd.DataFrame(fc).drop_duplicates(["publishTime", "startTime"])
fc.to_csv("data/forecast.csv", index=False)

fc["lead_h"] = (pd.to_datetime(fc.startTime) - pd.to_datetime(fc.publishTime)).dt.total_seconds() / 3600
print("actual rows:", len(act), "(expect 1488)")
print("forecast rows:", len(fc))
print("lead hours min/max:", fc.lead_h.min(), fc.lead_h.max())
print("forecasts published AFTER their target:", (fc.lead_h < 0).sum())
print("target minutes seen:", sorted(pd.to_datetime(fc.startTime).dt.minute.unique()))
print("versions per target, typical:", fc.groupby("startTime").size().describe()[["min", "50%", "max"]].tolist())