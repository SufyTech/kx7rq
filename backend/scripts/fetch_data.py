from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

B = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def get(name, **p):
    r = requests.get(f"{B}/{name}/stream", params=p, timeout=120)
    r.raise_for_status()
    d = r.json()
    return d["data"] if isinstance(d, dict) else d


def chunks(start, end, step):
    while start < end:
        yield start, min(start + timedelta(days=step), end)
        start += timedelta(days=step)


OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

# Actuals: Jan 1 - Feb 4 (extra days are the "truth" for forecasts published late in January)
act = []
for a, b in chunks(datetime(2026, 1, 1), datetime(2026, 2, 5), 5):
    act += get("FUELHH", settlementDateFrom=a.strftime("%Y-%m-%d"),
               settlementDateTo=(b - timedelta(days=1)).strftime("%Y-%m-%d"), fuelType="WIND")
act = pd.DataFrame(act).drop_duplicates(["startTime"]).sort_values("startTime")
act.to_csv(OUT / "actual.csv", index=False)

# Forecasts published Dec 25 - Jan 31 (decisions made in January use only these)
fc = []
for a, b in chunks(datetime(2025, 12, 25), datetime(2026, 2, 1), 2):
    fc += get("WINDFOR", publishDateTimeFrom=a.strftime("%Y-%m-%dT%H:%MZ"),
              publishDateTimeTo=b.strftime("%Y-%m-%dT%H:%MZ"))
fc = pd.DataFrame(fc).drop_duplicates(["publishTime", "startTime"])
fc.to_csv(OUT / "forecast.csv", index=False)

print("actual rows:", len(act), "(expect 1680)")
print("forecast rows:", len(fc))