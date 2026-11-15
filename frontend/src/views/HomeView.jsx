import FireMap from "../components/FireMap";
import YearlyChart from "../components/YearlyChart";
import { useApi } from "../lib/api";
import { fmt, weekLabel } from "../lib/format";

const HERO_VIEW = { center: [30.4, 72.6], zoom: 6 };

export default function HomeView({ meta, cells, metrics, heroWeek, go, openBox }) {
  const fc = useApi("forecast", { week: heroWeek, top: 1 });
  const record = useApi("calendar", { region: "all" });
  const viirsYear = Number(meta.viirs_start.slice(0, 4));
  const firstYear = Number(meta.calendar_weeks.first.slice(0, 4));
  const lastYear = Number(meta.calendar_weeks.last.slice(0, 4));
  const auc = metrics?.forecast_classification_test_2024_2025?.find((r) => r.method === "Model B")?.ROC_AUC;
  const s = fc.data?.summary;

  const facts = [
    { value: `${lastYear - firstYear + 1} years`, label: `of satellite fire records, ${firstYear} to ${lastYear}` },
    { value: fmt(meta.cells.total), label: "fire-prone places tracked, each a 25 km box" },
    { value: "8.5 million", label: "fire detections from MODIS and VIIRS" },
    { value: auc ? `${Math.round(auc * 100)}%` : "–", label: "of the time the forecast ranks a burning box above a quiet one" },
  ];

  const ways = [
    {
      id: "forecast",
      title: "See next week's fire risk",
      body: "Every box in Pakistan and India coloured by its chance of burning next week, with the reasons behind it and where the smoke will drift.",
      cta: "Open the forecast map",
    },
    {
      id: "calendar",
      title: "Read the burning calendar",
      body: "Twenty-six years of weekly burning for any area: its seasons, the weeks that broke the pattern, and the long-term trend.",
      cta: "Explore the calendar",
    },
    {
      id: "record",
      title: "Check the harmonized record",
      body: "How two satellites with different eyesight were joined into one consistent count, and the test that proves it works.",
      cta: "View the record",
    },
  ];

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-map">
          <FireMap
            cells={cells}
            forecast={fc.data}
            selected={null}
            onSelect={openBox}
            smog={null}
            scrollZoom={false}
            initialView={HERO_VIEW}
          />
        </div>
        <div className="hero-shade" aria-hidden="true" />
        <div className="hero-copy">
          <p className="kicker on-dark">NASA Space Apps Challenge 2026</p>
          <h1>Twenty-six years of fire, counted the same way.</h1>
          <p className="hero-lede">
            Satellites have watched fires across Pakistan and India since 2000, but two generations of sensors count them
            differently. Emberlog joins MODIS and VIIRS into one consistent record, forecasts next week's burning, and
            shows where the smoke is heading.
          </p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => go("forecast")}>
              Open the forecast map
            </button>
            <button className="btn-ghost" onClick={() => go("calendar")}>
              Explore the burning calendar
            </button>
          </div>
        </div>
        <p className="hero-caption">
          {s
            ? `Live forecast for the week of ${weekLabel(heroWeek)}: ${fmt(s.high_risk_boxes)} boxes at high risk, about ${fmt(s.expected_fires_punjab)} fires expected in Punjab. Click any box for details.`
            : "Loading the live forecast…"}
        </p>
      </section>

      <section className="facts" aria-label="Emberlog in numbers">
        {facts.map((f) => (
          <div key={f.label} className="fact">
            <span className="fact-value">{f.value}</span>
            <span className="fact-label">{f.label}</span>
          </div>
        ))}
      </section>

      <section className="home-section">
        <div className="home-section-head">
          <h2>The problem in one chart</h2>
          <p>
            Raw MODIS counts (grey) sit far below VIIRS (blue) because the newer sensor sees small fires the older one
            misses. Compare them directly and 2012 looks like the year burning exploded. The harmonized record (red)
            removes that false jump, so 2005 and 2025 can finally be compared fairly.
          </p>
        </div>
        {record.data ? (
          <YearlyChart yearly={record.data.yearly} viirsYear={viirsYear} height={320} />
        ) : (
          <p className="muted">Loading the record…</p>
        )}
      </section>

      <section className="home-section ways">
        {ways.map((w) => (
          <div key={w.id} className="way">
            <h3>{w.title}</h3>
            <p>{w.body}</p>
            <button className="link-btn" onClick={() => go(w.id)}>
              {w.cta}
            </button>
          </div>
        ))}
      </section>
    </div>
  );
}
