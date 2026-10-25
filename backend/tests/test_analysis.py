import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pandas as pd
from analysis import latest_before_cutoff, backtest

T = "2026-01-10 05:00"


def mk(rows):
    return pd.DataFrame([{"publishTime": pd.Timestamp(p, tz="UTC"),
                          "startTime": pd.Timestamp(s, tz="UTC"), "generation": g}
                         for p, s, g in rows])


def pick(rows, day="2026-01-10"):
    return latest_before_cutoff(mk(rows), day)


def test_picks_newest_before_cutoff():
    r = pick([("2026-01-08 12:00", T, 1), ("2026-01-09 06:00", T, 2), ("2026-01-09 11:59", T, 3)])
    assert r.generation.iloc[0] == 3


def test_ignores_forecast_after_cutoff():
    r = pick([("2026-01-09 06:00", T, 2), ("2026-01-09 12:01", T, 9)])
    assert r.generation.iloc[0] == 2


def test_cutoff_is_inclusive():
    assert pick([("2026-01-09 12:00", T, 5)]).generation.iloc[0] == 5


def test_no_valid_forecast_gives_empty():
    assert pick([("2026-01-09 15:00", T, 5)]).empty


def test_other_days_excluded():
    assert pick([("2026-01-09 06:00", "2026-01-11 05:00", 5)]).empty


def test_duplicate_rows_give_one_result():
    r = pick([("2026-01-09 06:00", T, 2), ("2026-01-09 06:00", T, 2)])
    assert len(r) == 1


def test_backtest_covers_decisions_made_in_january():
    rows = [("2025-12-31 06:00", "2026-01-01 05:00", 1),   # decision Dec 31 -> excluded
            ("2026-01-31 06:00", "2026-02-01 05:00", 2)]   # decision Jan 31 -> included
    actual = pd.Series([10, 20], name="actual",
                       index=pd.to_datetime(["2026-01-01 05:00", "2026-02-01 05:00"], utc=True))
    df = backtest(mk(rows), actual)
    assert list(df.index.strftime("%m-%d")) == ["02-01"]
    assert df.error.iloc[0] == -18


def test_backtest_empty_when_nothing_available():
    actual = pd.Series([10], name="actual", index=pd.to_datetime(["2026-01-05 05:00"], utc=True))
    assert backtest(mk([("2026-01-30 00:00", "2026-01-05 05:00", 1)]), actual).empty