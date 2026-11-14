import { useMemo, useState } from "react";
import FireMap from "../components/FireMap";
import WeekPicker from "../components/WeekPicker";
import BoxDetail from "../components/BoxDetail";
import SmogPanel from "../components/SmogPanel";
import { useApi } from "../lib/api";
import { fmt, pct, weekLabel, weekRange, ember, LEVEL_COLOR } from "../lib/format";

function Legend({ threshold }) {
  const stops = [0.1, 0.3, 0.5, 0.7, 0.9];
  return (
    <div className="legend">
      <span>Chance of fire next week</span>
      <div className="legend-bar">
        {stops.map((s) => (
          <i key={s} style={{ background: ember(s) }} />
        ))}
      </div>
      <div className="legend-ticks">
        <span>10%</span>
        <span>50%</span>
        <span>90%</span>
      </div>
      <span className="muted">High risk starts at {pct(threshold)}</span>
    </div>
  );
}

export default function ForecastView({ meta, cells, week, setWeek, selected, setSelected, openCalendar }) {
  const [city, setCity] = useState("Lahore");
  const [view, setView] = useState("punjab");

  const weeks = useMemo(
    () => weekRange(meta.forecast_weeks.first, meta.forecast_weeks.last),
    [meta.forecast_weeks.first, meta.forecast_weeks.last]
  );
  const presets = [
    { week: "2025-11-03", label: "Rice-straw peak, Nov 2025" },
    { week: "2025-05-05", label: "Wheat-straw peak, May 2025" },
    { week: meta.latest_forecast_week, label: "Latest week" },
  ].filter((p) => weeks.includes(p.week));

  const fc = useApi("forecast", { week, top: 8 });
  const smog = useApi("smog", { week, city });
  const f = fc.data;
  const s = f?.summary;

  return (
    <div className="forecast">
      <div className="map-wrap">
        <FireMap
          cells={cells}
          forecast={f}
          selected={selected}
          onSelect={setSelected}
          smog={smog.data}
          view={view}
        />
        <div className="map-controls">
          <button className={`seg ${view === "punjab" ? "seg-on" : ""}`} onClick={() => setView("punjab")}>
            Punjab
          </button>
          <button className={`seg ${view === "all" ? "seg-on" : ""}`} onClick={() => setView("all")}>
            Pakistan &amp; India
          </button>
        </div>
        {f && <Legend threshold={f.threshold} />}
        {fc.loading && <div className="map-loading">Running the model for {weekLabel(week)}…</div>}
      </div>

      <aside className="panel">
        <WeekPicker weeks={weeks} value={week} onChange={setWeek} presets={presets} />

        {fc.error && <p className="error">{fc.error}</p>}
        {s && (
          <section className="outlook">
            <p className="lede">
              <strong>{fmt(s.high_risk_boxes)} boxes</strong> are at high risk of fire in the week of{" "}
              {weekLabel(f.week)}: {fmt(s.high_risk_pakistan)} in Pakistan and {fmt(s.high_risk_india)} in India.
            </p>
            <p>
              The model expects about <strong>{fmt(s.expected_fires)}</strong> satellite fire detections,{" "}
              {fmt(s.expected_fires_punjab)} of them in the Punjab region.
              {f.has_actual && (
                <>
                  {" "}
                  Satellites later recorded <strong>{fmt(s.actual_fires)}</strong> ({fmt(s.actual_fires_punjab)} in
                  Punjab).
                </>
              )}
            </p>
          </section>
        )}

        {selected ? (
          <BoxDetail
            key={`${selected}-${week}`}
            cellId={selected}
            week={week}
            weatherEnabled={meta.weather_enabled}
            onClose={() => setSelected(null)}
            onOpenCalendar={openCalendar}
          />
        ) : (
          f && (
            <section className="top-list">
              <h2>Highest risk this week</h2>
              <p className="muted small">Select a place, or click any box on the map, to see why.</p>
              <ul>
                {f.top.map((t) => (
                  <li key={t.cell_id}>
                    <button onClick={() => setSelected(t.cell_id)}>
                      <span className="dot" style={{ background: LEVEL_COLOR[t.level] }} />
                      <span className="top-place">
                        {t.place_km} km from {t.place}
                        <span className="muted small">{t.country}</span>
                      </span>
                      <span className="top-num">
                        {pct(t.p)}
                        <span className="muted small">{fmt(t.expected, t.expected < 10 ? 1 : 0)} fires</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )
        )}

        <SmogPanel
          cities={meta.smog_cities}
          city={city}
          onCity={setCity}
          smog={smog.data}
          loading={smog.loading}
          error={smog.error}
        />
      </aside>
    </div>
  );
}
