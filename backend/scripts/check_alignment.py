import sys; sys.path.insert(0, "backend/app")
import pandas as pd
from analysis import load, backtest, metrics

actual, fc = load()
a = pd.read_csv("data/actual.csv")
a["startTime"] = pd.to_datetime(a.startTime, utc=True)
s = a.set_index("startTime").generation
for name, ser in [("hourly avg", actual), (":00 only", s[s.index.minute == 0])]:
    for k in (-1, 0, 1):
        m = metrics(backtest(fc, ser.rename("actual").shift(freq=f"{k}h")))
        print(name, "shift", k, "h -> MAE", round(m["mae"]), "bias", round(m["bias"]))