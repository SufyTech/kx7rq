# Day-ahead wind forecast monitor

A small web app for a UK energy utility that buys electricity on the day-ahead market. It answers two questions:

1. **What was the latest wind forecast I could see when I placed my order?**
2. **How wrong are forecasts like that, so I can plan for the error?**

Scope, as set by the brief: national-level **wind only**, **Elexon BMRS data only**, purchase decisions made in **January 2026**.

## Live app

- **Web app:** https://kx7rq-web.vercel.app/
- **API (health check):** https://kx7rq.vercel.app/api/health

The web app and the API are two separate Vercel projects built from this one repo. The web app forwards `/api/*` requests to the API (see `frontend/vercel.json`).

## Use of AI tools

AI tools were used in this project. **Claude (Anthropic)** assisted with planning, writing and debugging code, and drafting this README. The analysis logic is covered by automated tests (see below), and results were checked by running the test suite and inspecting the output in the running app.

## What the app shows

- **Forecast tab:** pick a decision date (any day in January 2026) and a decision time. The app shows the forecast you could actually see at that moment, for delivery the next day, next to what was really generated.
- **Accuracy tab:** how far off the forecasts were across every January decision, as a typical miss (MAE), a big-miss measure (RMSE), the average bias, and a suggested buffer (the 90th percentile of the absolute error).

### Headline results (decision cutoff 12:00 UTC, 744 hourly deliveries)

| Measure                               | Value                               |
| ------------------------------------- | ----------------------------------- |
| Hours tested                          | 744                                 |
| MAE (typical miss)                    | about 1,901 MW                      |
| RMSE                                  | about 2,359 MW                      |
| Bias (forecast minus actual)          | about +1,687 MW (forecast too high) |
| P90 absolute error (suggested buffer) | about 3,847 MW                      |

The typical miss grows with forecast age, from roughly 1,750 MW for forecasts made 0-6 hours before the target hour to roughly 2,300 MW for the oldest groups. The bias is positive in every age group.

## How the data is used

- **Actuals:** Elexon `FUELHH`, rows with `fuelType = WIND`, fields `startTime` and `generation`.
- **Forecasts:** Elexon `WINDFOR`, fields `startTime`, `publishTime` and `generation`.
- **Core rule:** for each delivery hour, use the **newest forecast whose `publishTime` is at or before the decision time**. A forecast published after the decision time is never used. A test proves this.
- **Decision time:** the order is placed on the day before delivery, at a cutoff hour that can be changed in the UI.

### Assumptions and limits (please read)

1. **Decision cutoff defaults to 12:00 UTC on the day before delivery.** The brief gives no time, so this is my assumption. It can be changed in the UI. I have not verified the real auction closing time.
2. **"Decisions made in January 2026"** means decision days 1-31 January, so deliveries run from 2 January to 1 February. This gives 744 hourly points.
3. **WINDFOR is hourly, FUELHH is half-hourly.** Actuals are averaged to hourly. I assume each forecast value represents that hour; I have not confirmed this from the Elexon documentation.
4. **Some forecasts have a `publishTime` after their target time.** The cutoff rule excludes them automatically. I do not know why Elexon publishes them.
5. **Time zone:** January is UTC = UK time, so there are no daylight-saving issues. Everything is in UTC.
6. **Forecasts run high on average.** An alignment check (shifting actuals by plus or minus one hour) did not remove the bias, so it is not a simple time-alignment error. **I did not investigate the cause.** The two Elexon datasets may differ in scope. The bias is positive at every forecast age but not constant: it is lower for the oldest groups.
7. **Data window:** actuals were downloaded through 4 February and forecasts published from 25 December to 31 January. Actuals after 1 February are needed as the truth for forecasts published late in January.
8. **Error by forecast age** uses forecasts published in January only, in 6-hour groups. Groups with fewer than 100 points are hidden.

## Files and directories

| Path                                             | What it is                                                                                                                                |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/app/analysis.py`                        | Core logic: pick the newest forecast before the cutoff, average actuals to hourly, compute MAE, RMSE, bias, P90 and error by forecast age |
| `backend/app/main.py`                            | FastAPI app and API routes. Also serves the built React app when a `static` folder exists (used in Docker)                                |
| `backend/data/actual.csv`                        | Downloaded Elexon FUELHH wind actuals                                                                                                     |
| `backend/data/forecast.csv`                      | Downloaded Elexon WINDFOR wind forecasts                                                                                                  |
| `backend/tests/test_analysis.py`                 | 8 automated tests for the analysis logic                                                                                                  |
| `backend/scripts/fetch_data.py`                  | Script that downloads the data from the Elexon API into `backend/data`                                                                    |
| `backend/scripts/check_alignment.py`             | One-off check used to test whether the forecast bias was a time-alignment error                                                           |
| `backend/scripts/probe.py`                       | Early script used to explore the Elexon API                                                                                               |
| `backend/requirements.txt`                       | Runtime Python dependencies                                                                                                               |
| `backend/requirements-dev.txt`                   | Runtime dependencies plus test and data-download tools                                                                                    |
| `frontend/src/App.jsx`                           | The React app (both tabs)                                                                                                                 |
| `frontend/src/main.jsx`, `index.css`, `App.css`  | React entry point and styles                                                                                                              |
| `frontend/vite.config.js`                        | Vite config. In local development it proxies `/api` to the backend on port 8000                                                           |
| `frontend/vercel.json`                           | Vercel rewrite that forwards `/api/*` to the deployed API                                                                                 |
| `frontend/package.json`, `package-lock.json`     | Frontend dependencies and scripts                                                                                                         |
| `frontend/index.html`, `public/`, `src/assets/`  | HTML shell and static assets (mostly from the Vite template)                                                                              |
| `frontend/.oxlintrc.json`, `frontend/.gitignore` | Lint config and ignore rules for the frontend                                                                                             |
| `Dockerfile`                                     | Builds the frontend and serves the whole app from one Python server                                                                       |
| `docker-compose.yml`                             | Runs the Docker image on port 8000                                                                                                        |
| `.dockerignore`, `.gitignore`                    | Ignore rules                                                                                                                              |
| `.github/workflows/ci.yml`                       | GitHub Actions pipeline (see "Testing and CI")                                                                                            |

## API

| Endpoint                                                     | Purpose                                                                                                                       |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/health`                                            | Health check                                                                                                                  |
| `GET /api/forecast?decision_date=&cutoff_hour=&days_before=` | Hourly forecast, actual and publish time for the delivery day. Returns 422 for a date outside January 2026 or an invalid hour |
| `GET /api/accuracy?cutoff_hour=&days_before=`                | `n`, `mae`, `rmse`, `bias`, `p90_abs` over every January decision                                                             |
| `GET /api/horizon`                                           | Error by forecast age                                                                                                         |

## How to start the application

### Option 1: Docker (one server, app on port 8000)

```
docker compose up --build
```

Then open http://localhost:8000. The Docker build and a health check run in GitHub Actions on every push.

### Option 2: run backend and frontend separately

Backend (Python 3.11 or newer), from the repo root:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

On macOS or Linux, activate with `source .venv/bin/activate`. Check it works at http://127.0.0.1:8000/api/health.

Frontend (Node.js), in a second terminal, from the repo root:

```
cd frontend
npm install
npm run dev
```

Open the address Vite prints (usually http://localhost:5173). In development, Vite forwards `/api` requests to the backend on port 8000.

### Run the tests

```
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

## Testing and CI

The 8 tests cover the logic that matters most:

- picks the newest forecast published before the cutoff
- ignores a forecast published after the cutoff
- the cutoff is inclusive
- returns nothing when no forecast is valid
- other delivery days are excluded
- duplicate forecasts give one row
- the backtest covers decisions made in January (31 December excluded, 31 January included)
- the backtest is empty when no data is available

GitHub Actions (`.github/workflows/ci.yml`) runs three jobs on every push: backend tests, frontend build, and a Docker build with a health check.

## Next steps

- Confirm the real day-ahead auction cutoff time and set it as the default.
- Investigate the forecast bias (differences in scope between the two datasets).
- Break the error down by season, time of day and wind level.
- Add monitoring so the data and accuracy figures update automatically.
