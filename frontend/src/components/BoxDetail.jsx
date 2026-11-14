import { useEffect, useRef } from "react";
import { X, CloudRain, Wind, Thermometer, Droplets } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../lib/api";
import { fmt, pct, weekLabel, LEVEL_COLOR, EMBER, BLUE, SLATE, compassName } from "../lib/format";

function Factors({ factors }) {
  const top = factors.slice(0, 6);
  const max = Math.max(...top.map((f) => Math.abs(f.contribution)), 0.001);
  return (
    <ul className="factors">
      {top.map((f) => {
        const w = (Math.abs(f.contribution) / max) * 100;
        const up = f.contribution > 0;
        return (
          <li key={f.feature}>
            <div className="factor-text">
              <span>{f.label}</span>
              <span className="muted">{f.value === null ? "–" : fmt(f.value, f.value < 10 ? 1 : 0)}</span>
            </div>
            <div className="factor-track">
              <div className={`factor-bar ${up ? "up" : "down"}`} style={{ width: `${w}%` }} />
            </div>
            <span className={`factor-dir ${up ? "up" : "down"}`}>{up ? "raises risk" : "lowers risk"}</span>
          </li>
        );
      })}
    </ul>
  );
}

function History({ history, week }) {
  const data = history.map((h) => ({ ...h, label: weekLabel(h.week, false) }));
  return (
    <div className="chart-sm">
      <ResponsiveContainer width="100%" height={170}>
        <ComposedChart data={data} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#E6E6E6" />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: SLATE }} interval={3} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 11, fill: SLATE }} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip
            formatter={(v, n) => [fmt(v, 0), n]}
            labelFormatter={(l, p) => (p && p[0] ? `Week of ${weekLabel(p[0].payload.week)}` : l)}
          />
          <ReferenceLine x={weekLabel(week, false)} stroke="#000" strokeDasharray="3 3" />
          <Bar dataKey="fires" name="This season" fill={EMBER[2]} />
          <Line dataKey="last_year" name="Same weeks last year" stroke={BLUE} strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function Weather({ lat, lon, week }) {
  const { data, loading } = useApi("weather", { lat, lon, start: week });
  if (loading) return <p className="muted">Loading weather…</p>;
  if (!data || !data.available) return <p className="muted">Weather is unavailable for this box right now.</p>;
  const s = data.summary;
  const mainDir = data.days.find((d) => d.wind_dir_deg !== null)?.wind_dir_deg;
  const verdict = {
    dry: "Dry week: conditions favour burning.",
    wet: "Wet week: rain makes burning less likely.",
    mixed: "Mixed week: some rain, some dry days.",
  }[s.burning_conditions];
  return (
    <div className="weather">
      <p>
        <strong>{verdict}</strong> {fmt(s.total_rain_mm, 1)} mm of rain over 7 days, humidity around{" "}
        {fmt(s.mean_humidity_pct)}%{mainDir !== undefined ? `, wind mostly from the ${compassName(mainDir)}` : ""}.
        {s.spread_risk === "high" ? " Strong winds can spread fire and smoke quickly." : ""}
      </p>
      <div className="weather-days">
        {data.days.map((d) => (
          <div key={d.date} className="wday">
            <span className="wday-name">
              {new Date(`${d.date}T00:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" })}
            </span>
            <span title="Temperature">
              <Thermometer size={13} /> {fmt(d.t_max)}°
            </span>
            <span title="Rain">
              <CloudRain size={13} /> {fmt(d.precip_mm, 1)}
            </span>
            <span title="Wind">
              <Wind size={13} /> {fmt(d.wind_speed_ms, 1)}
            </span>
            <span title="Humidity">
              <Droplets size={13} /> {fmt(d.humidity_pct)}%
            </span>
          </div>
        ))}
      </div>
      <p className="source">Weather by Meteomatics</p>
    </div>
  );
}

export default function BoxDetail({ cellId, week, weatherEnabled, onClose, onOpenCalendar }) {
  const { data, error, loading } = useApi("explain", { cell_id: cellId, week });
  const ref = useRef(null);

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [cellId]);

  return (
    <section className="detail" aria-live="polite" ref={ref}>
      <div className="detail-head">
        <h2>{data ? `${data.place_km} km from ${data.place}` : "Selected box"}</h2>
        <button className="icon-btn" onClick={onClose} aria-label="Close box details">
          <X size={18} />
        </button>
      </div>
      {loading && !data && <p className="muted">Working out the forecast for this box…</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <p className="muted small">
            {data.country}, around {data.lat.toFixed(2)}°N {data.lon.toFixed(2)}°E, a 25 km box
          </p>
          <div className="stat-row">
            <div className="stat">
              <span className={`stat-value level-${data.level.replace(" ", "-")}`}>
                {pct(data.probability)}
              </span>
              <span className="stat-label">chance of fire</span>
            </div>
            <div className="stat">
              <span className="stat-value">{fmt(data.expected_fires, data.expected_fires < 10 ? 1 : 0)}</span>
              <span className="stat-label">fires expected</span>
            </div>
            <div className="stat">
              <span className="stat-value">{data.actual_fires === null ? "–" : fmt(data.actual_fires)}</span>
              <span className="stat-label">{data.actual_fires === null ? "not yet observed" : "actually seen"}</span>
            </div>
          </div>
          <p className="summary">{data.summary}</p>

          <h3>Why the model says this</h3>
          <Factors factors={data.factors} />

          <h3>This box, week by week</h3>
          <History history={data.history} week={data.week} />

          {weatherEnabled && (
            <>
              <h3>Weather that week</h3>
              <Weather lat={data.lat} lon={data.lon} week={data.week} />
            </>
          )}

          <button className="btn-secondary" onClick={() => onOpenCalendar(cellId)}>
            See this box's 26-year burning calendar
          </button>
        </>
      )}
    </section>
  );
}
