import { fmt } from "../lib/format";
import PageHeader from "../components/PageHeader";

const STEPS = [
  {
    title: "Collect every fire the satellites saw",
    body: "NASA FIRMS active-fire records for Pakistan and India: MODIS from November 2000 and VIIRS S-NPP from January 2012. We keep vegetation fires only, so factories, gas flares and volcanoes are left out, and drop low-confidence detections.",
  },
  {
    title: "Lay a grid over the map",
    body: "Pakistan and India are split into 0.25° boxes, about 25 km across, and fires are counted per box per week. That gives 5,381 fire-prone boxes and 1,314 weeks.",
  },
  {
    title: "Harmonize MODIS into VIIRS terms",
    body: "A LightGBM model learns, from 2012 onward where both satellites overlap, how many fires VIIRS would see given what MODIS saw. A second model covers late 2000 to mid 2002, when only the Terra satellite was flying.",
  },
  {
    title: "Forecast next week",
    body: "Two LightGBM models use only the past: fires in the box over recent weeks, fires in the eight neighbouring boxes, the same week last year, the five-year average for that week, and the time of year. One gives the chance of fire, the other the expected number of fires.",
  },
  {
    title: "Explain every prediction",
    body: "SHAP values show how much each clue pushed a box's risk up or down, and the site turns the strongest ones into a plain sentence.",
  },
  {
    title: "Add weather and smoke direction",
    body: "Meteomatics weather shows rain, humidity and wind for the selected week. Wind direction tells us whether smoke from predicted fires is likely to drift toward a city such as Lahore.",
  },
];

const FORECAST_COLS = [
  ["ROC_AUC", "Ranking (ROC-AUC)"],
  ["PR_AUC", "Precision-recall AUC"],
  ["Recall", "Fires caught"],
  ["F1", "F1"],
];

const NAMES = {
  "Persistence (fire this week)": "Repeat this week",
  "Climatology (5-yr same week)": "Five-year average",
  "Model B": "Our forecast model",
  "Model B (Punjab only)": "Our model, Punjab only",
};

export default function MethodView({ metrics }) {
  const cls = metrics?.forecast_classification_test_2024_2025 || [];
  return (
    <>
      <PageHeader kicker="Method" title="How FireSync works">
        Built for the 2026 NASA Space Apps Challenge, Harmonization of MODIS and VIIRS Hot Spots. Every number on this
        site comes from open NASA satellite data.
      </PageHeader>
    <div className="page method">
      <ol className="steps">
        {STEPS.map((s) => (
          <li key={s.title}>
            <h2>{s.title}</h2>
            <p>{s.body}</p>
          </li>
        ))}
      </ol>

      {cls.length > 0 && (
        <section>
          <h2>How good is the forecast?</h2>
          <p>Tested on 2024 to 2025, weeks the model never saw during training. Higher is better on every column.</p>
          <div className="table-wrap">
            <table className="metrics">
              <thead>
                <tr>
                  <th scope="col">Method</th>
                  {FORECAST_COLS.map(([k, l]) => (
                    <th key={k} scope="col">{l}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cls.map((r) => (
                  <tr key={r.method} className={r.method.startsWith("Model B") ? "ours" : ""}>
                    <th scope="row">{NAMES[r.method] || r.method}</th>
                    {FORECAST_COLS.map(([k]) => (
                      <td key={k}>{k === "Recall" ? `${fmt(r[k] * 100)}%` : fmt(r[k], 2)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section>
        <h2>What it can't do</h2>
        <ul className="plain">
          <li>
            It learns from history, so sudden changes in behaviour fool it. In autumn 2024, burning in Punjab fell far
            below past years and the model over-predicted the peak.
          </li>
          <li>Estimates before mid 2002 rest on one satellite and are less certain than later years.</li>
          <li>Satellites only see fires burning when they pass overhead; fires lit after the pass can be missed.</li>
          <li>The smoke index is a guide to where smoke is heading, not an air-quality measurement.</li>
        </ul>
      </section>

      <section className="credits">
        <h2>Data and team</h2>
        <p>
          Fire data: NASA FIRMS, MODIS Collection 6.1 and VIIRS S-NPP 375 m active fires. Weather: Meteomatics. Map:
          NASA Black Marble via GIBS, Esri and OpenStreetMap contributors.
        </p>
        <p>Team: Waqar Ahmed, Zohaib Ahmed, Muhammad Hassan and Sakhi Ghulam.</p>
      </section>
    </div>
    </>
  );
}
