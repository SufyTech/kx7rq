import requests, json

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

def probe(name, params):
    r = requests.get(f"{BASE}/{name}/stream", params=params, timeout=60)
    print("\n==", name, r.status_code, r.url)
    if r.status_code != 200:
        print(r.text[:500]); return
    d = r.json()
    rows = d["data"] if isinstance(d, dict) and "data" in d else d
    print("rows:", len(rows))
    print(json.dumps(rows[:2], indent=1))

probe("FUELHH", {"settlementDateFrom": "2026-01-01",
                 "settlementDateTo": "2026-01-02",
                 "fuelType": "WIND"})
probe("WINDFOR", {"publishDateTimeFrom": "2025-12-31T00:00Z",
                  "publishDateTimeTo": "2026-01-01T12:00Z"})