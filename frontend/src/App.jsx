import { useEffect, useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import "./App.css";

const mw = (n) => `${Math.round(n).toLocaleString("en-GB")} MW`;
const pad = (h) => String(h).padStart(2, "0");
const day = (iso) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });

function useApi(url) {
  const [s, setS] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let live = true;
    setS((p) => ({ ...p, loading: true, error: null }));
    fetch(url)
      .then((r) =>
        r
          .json()
          .then((j) =>
            r.ok
              ? j
              : Promise.reject(
                  new Error(
                    typeof j.detail === "string" ? j.detail : "Invalid input",
                  ),
                ),
          ),
      )
      .then((data) => live && setS({ data, error: null, loading: false }))
      .catch(
        (e) =>
          live &&
          setS({
            data: null,
            error: e.message || "Cannot reach the server",
            loading: false,
          }),
      );
    return () => {
      live = false;
    };
  }, [url]);
  return s;
}

const Status = ({ s }) =>
  s.loading ? (
    <div className="load">Loading…</div>
  ) : s.error ? (
    <div className="err">Something went wrong: {s.error}</div>
  ) : null;

const Kpi = ({ label, value, hint }) => (
  <div className="kpi">
    <span>{label}</span>
    <b>{value}</b>
    <small>{hint}</small>
  </div>
);

const axis = { tick: { fill: "#64748b", fontSize: 12 }, stroke: "#cbd5e1" };
const tip = { contentStyle: { borderRadius: 10, border: "1px solid #e2e8f0" } };

function Forecast({ date, hour }) {
  const s = useApi(`/api/forecast?decision_date=${date}&cutoff_hour=${hour}`);
  const pts =
    s.data?.points.map((p) => ({ ...p, hour: p.time.slice(11, 16) })) ?? [];
  const avg = (k) =>
    pts.reduce((a, p) => a + (p[k] ?? 0), 0) /
    (pts.filter((p) => p[k] != null).length || 1);
  const pubs = pts.map((p) => p.published).sort();
  return (
    <>
      <Status s={s} />
      {s.data && pts.length === 0 && (
        <div className="card">
          No forecast had been published by this decision time.
        </div>
      )}
      {pts.length > 0 && (
        <>
          <div className="kpis">
            <Kpi
              label="Delivery day"
              value={day(s.data.delivery_day)}
              hint="what you are buying for"
            />
            <Kpi
              label="Avg forecast wind"
              value={mw(avg("forecast"))}
              hint="latest forecast you could see"
            />
            <Kpi
              label="Avg actual wind"
              value={mw(avg("actual"))}
              hint="what really generated"
            />
            <Kpi
              label="Avg gap"
              value={mw(avg("forecast") - avg("actual"))}
              hint="forecast minus actual"
            />
          </div>
          <div className="card">
            <h3>Wind generation: forecast vs actual</h3>
            <p className="sub">
              Hourly, UTC. Each hour uses the newest forecast published before
              your decision time.
            </p>
            <ResponsiveContainer width="100%" height={360}>
              <ComposedChart data={pts}>
                <defs>
                  <linearGradient id="act" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="hour" {...axis} />
                <YAxis
                  {...axis}
                  domain={["dataMin - 1000", "dataMax + 1000"]}
                  tickFormatter={(v) => `${Math.round(v / 1000)}`}
                  label={{
                    value: "GW",
                    angle: -90,
                    position: "insideLeft",
                    fill: "#64748b",
                  }}
                />
                <Tooltip {...tip} formatter={(v) => mw(v)} />
                <Legend />
                <Area
                  dataKey="actual"
                  name="Actual"
                  stroke="#059669"
                  strokeWidth={2}
                  fill="url(#act)"
                />
                <Line
                  dataKey="forecast"
                  name="Forecast"
                  stroke="#2563eb"
                  strokeWidth={3}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="note">
              Forecasts used were published between{" "}
              {pubs[0].replace("T", " ").slice(0, 16)} and{" "}
              {pubs.at(-1).replace("T", " ").slice(0, 16)} UTC, all at or before
              the decision time (
              {s.data.decision_time.replace("T", " ").slice(0, 16)} UTC).
            </p>
          </div>
        </>
      )}
    </>
  );
}

function Accuracy({ hour }) {
  const a = useApi(`/api/accuracy?cutoff_hour=${hour}`);
  const h = useApi("/api/horizon");
  const bars = h.data?.map((r) => ({
    ...r,
    label: `${r.bucket}–${r.bucket + 6}h`,
  }));
  const d = a.data;
  return (
    <>
      <Status s={a} />
      {d && (
        <>
          <div className="banner">
            <b>Plan for a buffer of about {mw(d.p90_abs)}.</b>
            <br />
            In 90% of hours in January, the forecast you could see was within
            that of the actual. On average it ran {mw(Math.abs(d.bias))}{" "}
            {d.bias > 0 ? "too high" : "too low"}.
          </div>
          <div className="kpis">
            <Kpi
              label="Typical miss (MAE)"
              value={mw(d.mae)}
              hint="average size of the error"
            />
            <Kpi
              label="Big-miss weighted (RMSE)"
              value={mw(d.rmse)}
              hint="punishes large errors more"
            />
            <Kpi
              label="Bias"
              value={`${d.bias > 0 ? "+" : ""}${Math.round(d.bias).toLocaleString("en-GB")} MW`}
              hint="+ means forecast too high"
            />
            <Kpi
              label="Hours tested"
              value={d.n.toLocaleString("en-GB")}
              hint="every purchase decision in Jan 2026"
            />
          </div>
        </>
      )}
      <div className="card">
        <h3>Error by how early the forecast was made</h3>
        <p className="sub">
          Forecasts published in January 2026, grouped by hours before the
          target hour.
        </p>
        <Status s={h} />
        {bars && (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={bars}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" {...axis} />
              <YAxis
                {...axis}
                tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              />
              <Tooltip {...tip} formatter={(v) => mw(v)} />
              <Legend />
              <Bar
                dataKey="mae"
                name="Typical miss (MAE)"
                fill="#2563eb"
                radius={[6, 6, 0, 0]}
              />
              <Line
                dataKey="bias"
                name="Bias"
                stroke="#d97706"
                strokeWidth={3}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
        <p className="note">
          Groups with fewer than 100 data points are hidden. The cause of the
          bias was not investigated; the two Elexon datasets may differ in
          scope.
        </p>
      </div>
      <div className="card">
        <h3>How to read these numbers</h3>
        <div className="defs">
          <div>
            <b>MAE</b>The average size of the miss, ignoring direction.
          </div>
          <div>
            <b>RMSE</b>Like MAE, but large misses count more.
          </div>
          <div>
            <b>Bias</b>Average of forecast minus actual. Positive means the
            forecast was too high.
          </div>
          <div>
            <b>Buffer (P90)</b>The miss was smaller than this in 9 of 10 hours.
          </div>
        </div>
      </div>
    </>
  );
}

export default function App() {
  const [tab, setTab] = useState("forecast");
  const [date, setDate] = useState("2026-01-09");
  const [hour, setHour] = useState(12);
  const next = new Date(`${date}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  const deliveryIso = next.toISOString().slice(0, 10);
  return (
    <>
      <header className="hero">
        <div className="inner">
          <span className="pill">Pilot · January 2026 · Elexon BMRS data</span>
          <h1>Day-ahead wind forecast monitor</h1>
          <p>
            See the wind forecast you actually had when you placed your
            day-ahead order, and how far off forecasts like it tend to be.
          </p>
        </div>
      </header>
      <main className="main">
        <div className="panel">
          {tab === "forecast" && (
            <label>
              Decision date
              <input
                type="date"
                value={date}
                min="2026-01-01"
                max="2026-01-31"
                onChange={(e) => e.target.value && setDate(e.target.value)}
              />
            </label>
          )}
          <label>
            Decision time (UTC)
            <select
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
            >
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>
                  {pad(i)}:00
                </option>
              ))}
            </select>
          </label>
          <div className="flow">
            {tab === "forecast" ? (
              <>
                You place your order on <b>{day(date)}</b> at{" "}
                <b>{pad(hour)}:00 UTC</b> for delivery on{" "}
                <b>{day(deliveryIso)}</b>.
              </>
            ) : (
              <>
                Every January decision made at <b>{pad(hour)}:00 UTC</b>, for
                delivery the next day.
              </>
            )}
          </div>
        </div>
        <div className="tabs">
          <button
            className={tab === "forecast" ? "on" : ""}
            onClick={() => setTab("forecast")}
          >
            Forecast vs actual
          </button>
          <button
            className={tab === "accuracy" ? "on" : ""}
            onClick={() => setTab("accuracy")}
          >
            Forecast accuracy
          </button>
        </div>
        {tab === "forecast" ? (
          <Forecast date={date} hour={hour} />
        ) : (
          <Accuracy hour={hour} />
        )}
      </main>
      <footer>
        Source: Elexon BMRS (FUELHH actuals, WINDFOR forecasts). National-level
        wind only.
      </footer>
    </>
  );
}
