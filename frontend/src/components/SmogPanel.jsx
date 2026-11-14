import { fmt, LEVEL_COLOR, EMBER } from "../lib/format";

const LEVEL_TEXT = {
  low: "Low smoke risk",
  moderate: "Moderate smoke risk",
  high: "High smoke risk",
  "very high": "Very high smoke risk",
};

export default function SmogPanel({ cities, city, onCity, smog, loading, error }) {
  return (
    <section className="smog">
      <div className="smog-head">
        <h2>Smoke heading for</h2>
        <select value={city} onChange={(e) => onCity(e.target.value)} aria-label="City for smoke warning">
          {cities.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>
      {loading && !smog && <p className="muted">Checking fires and wind around {city}…</p>}
      {error && <p className="error">{error}</p>}
      {smog && (
        <>
          <div className="smog-level">
            <span className="dot" style={{ background: LEVEL_COLOR[smog.level] || EMBER[1] }} />
            <strong>{LEVEL_TEXT[smog.level]}</strong>
          </div>
          <p>
            About {fmt(smog.expected_fires_nearby)} fires are expected within 400 km of {smog.city.name} this week.
            {smog.wind_used
              ? ` ${smog.upwind_boxes} fire-prone boxes are upwind, so their smoke is likely to drift toward the city.`
              : " Wind data isn't available, so this estimate uses distance only."}
          </p>
          {smog.sources.length > 0 && (
            <>
              <p className="muted small">Biggest likely smoke sources</p>
              <ol className="sources">
                {smog.sources.slice(0, 4).map((s) => (
                  <li key={s.cell_id}>
                    <span>Near {s.place}</span>
                    <span className="muted">
                      {s.dist_km} km away, {fmt(s.expected, s.expected < 10 ? 1 : 0)} fires expected
                    </span>
                  </li>
                ))}
              </ol>
            </>
          )}
          <p className="source">{smog.method}</p>
        </>
      )}
    </section>
  );
}
