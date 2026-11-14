import { useMemo } from "react";
import RegionPicker, { regionParams } from "../components/RegionPicker";
import PageHeader from "../components/PageHeader";
import YearlyChart from "../components/YearlyChart";
import { useApi } from "../lib/api";
import { fmt } from "../lib/format";

const COLS = [
  ["cell_MAE", "Error per box (MAE)", false],
  ["cell_R2", "Box accuracy (R²)", true],
  ["weekly_total_R2", "Weekly total (R²)", true],
  ["punjab_weekly_R2", "Punjab weekly (R²)", true],
];

function MetricsTable({ rows }) {
  if (!rows || !rows.length) return null;
  const pairs = [
    ["Baseline ratio (MODIS x k)", "Model A full (Terra+Aqua)", "2002 onward, both MODIS satellites"],
    ["Baseline ratio (Terra x k)", "Model A Terra-only", "Nov 2000 to Jun 2002, Terra only"],
  ];
  const by = Object.fromEntries(rows.map((r) => [r.method, r]));
  return (
    <div className="table-wrap">
      <table className="metrics">
        <thead>
          <tr>
            <th scope="col">Method</th>
            {COLS.map(([k, label]) => (
              <th key={k} scope="col">{label}</th>
            ))}
          </tr>
        </thead>
        {pairs.map(([base, model, caption]) =>
          by[base] && by[model] ? (
            <tbody key={model}>
              <tr className="group">
                <th colSpan={5} scope="rowgroup">{caption}</th>
              </tr>
              <tr>
                <th scope="row">Multiply MODIS by a fixed ratio</th>
                {COLS.map(([k]) => (
                  <td key={k}>{fmt(by[base][k], 2)}</td>
                ))}
              </tr>
              <tr className="ours">
                <th scope="row">Our harmonization model</th>
                {COLS.map(([k, , higher]) => {
                  const better = higher ? by[model][k] > by[base][k] : by[model][k] < by[base][k];
                  return (
                    <td key={k} className={better ? "better" : ""}>
                      {fmt(by[model][k], 2)}
                    </td>
                  );
                })}
              </tr>
            </tbody>
          ) : null
        )}
      </table>
    </div>
  );
}

export default function RecordView({ meta, metrics, region, setRegion, selectedCell }) {
  const params = useMemo(() => regionParams(region), [region]);
  const { data: cal, error, loading } = useApi("calendar", params);
  const viirsYear = Number(meta.viirs_start.slice(0, 4));

  return (
    <>
      <PageHeader
        kicker="Harmonization"
        title="One record from two satellites"
        aside={<RegionPicker regions={meta.regions} value={region} onChange={setRegion} selectedCell={selectedCell} dark />}
      >
        MODIS has watched fires since 2000. VIIRS joined in 2012 and, with sharper eyes, sees about five times more of
        them. Side by side, the raw records make burning look like it exploded in 2012. Our model learns how the two
        relate where both were watching, then rewrites the early years in VIIRS terms.
      </PageHeader>

      <div className="page">
        {error && <p className="error">{error}</p>}
        {loading && !cal && <p className="muted">Loading the record…</p>}

        {cal && (
          <section className="block">
            <div className="block-head">
              <h2>Fires per year, {cal.label}</h2>
              <p className="muted">Grey years have no VIIRS data; their harmonized values are model estimates.</p>
            </div>
            <YearlyChart yearly={cal.yearly} viirsYear={viirsYear} />
          </section>
        )}

        <section className="block">
          <div className="block-head">
            <h2>Does the model beat simple scaling?</h2>
            <p className="muted">
              Trained on 2012 to 2021, tuned on 2022 to 2023, tested on 2024 to 2025, which the model never saw. Higher
              R² and lower error are better.
            </p>
          </div>
          <MetricsTable rows={metrics?.harmonization_test_2024_2025} />
        </section>
      </div>
    </>
  );
}
