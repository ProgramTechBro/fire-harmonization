import { useMemo, useState } from "react";
import { ember, fmt } from "../lib/format";

const CELL = 13;
const GAP = 2;
const LEFT = 64;
const TOP = 22;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function isoWeekOfMonthStart(m) {
  const d = new Date(Date.UTC(2025, m, 1));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
}

export function weekToDate(year, w) {
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const day = jan4.getUTCDay() || 7;
  const monday = new Date(jan4);
  monday.setUTCDate(jan4.getUTCDate() - day + 1 + (w - 1) * 7);
  return monday;
}

export default function Heatmap({ heatmap, viirsStart = 2012, selectedYear, onYear }) {
  const [hover, setHover] = useState(null);
  const rows = heatmap.years
    .map((y, i) => ({ y, v: heatmap.values[i] }))
    .filter((r) => r.v.filter((x) => x !== null).length >= 8);
  const years = rows.map((r) => r.y);
  const values = rows.map((r) => r.v);
  const max = useMemo(() => {
    let m = 0;
    values.forEach((row) => row.forEach((v) => { if (v !== null && v > m) m = v; }));
    return m;
  }, [values]);
  const scale = (v) => (max > 0 ? Math.sqrt(v / max) : 0);
  const width = LEFT + 53 * (CELL + GAP);
  const height = TOP + years.length * (CELL + GAP);

  return (
    <div className="heatmap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Fires per week for every year">
        {MONTHS.map((m, i) => (
          <text key={m} x={LEFT + (isoWeekOfMonthStart(i) - 1) * (CELL + GAP)} y={13} className="hm-month">
            {m}
          </text>
        ))}
        {years.map((y, r) => {
          const est = y < viirsStart;
          const yPos = TOP + r * (CELL + GAP);
          return (
            <g key={y} onClick={() => onYear(y)} className="hm-row">
              <text x={LEFT - 8} y={yPos + CELL - 2} textAnchor="end" className={`hm-year ${est ? "est" : ""} ${y === selectedYear ? "sel" : ""}`}>
                {y}
                {est ? "*" : ""}
              </text>
              {values[r].map((v, c) =>
                v === null ? null : (
                  <rect
                    key={c}
                    x={LEFT + c * (CELL + GAP)}
                    y={yPos}
                    width={CELL}
                    height={CELL}
                    rx={2}
                    fill={scale(v) < 0.08 ? "#ECECEC" : ember(scale(v))}
                    onMouseEnter={() => setHover({ y, w: c + 1, v, est })}
                    onMouseLeave={() => setHover(null)}
                  />
                )
              )}
              {y === selectedYear && (
                <rect x={LEFT - 3} y={yPos - 2} width={53 * (CELL + GAP) + 3} height={CELL + 4} rx={4} className="hm-sel" />
              )}
            </g>
          );
        })}
      </svg>
      <div className="hm-foot">
        <span className="hm-readout">
          {hover
            ? `Week of ${weekToDate(hover.y, hover.w).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })}: ${fmt(hover.v, hover.v < 10 ? 1 : 0)} fires${hover.est ? " (estimated from MODIS)" : ""}`
            : "Point at a square to read its value. Click a year to see it in detail."}
        </span>
        <span className="hm-scale">
          <span className="muted">Fewer</span>
          {[0, 0.2, 0.45, 0.7, 1].map((t) => (
            <i key={t} style={{ background: t === 0 ? "#ECECEC" : ember(t) }} />
          ))}
          <span className="muted">More fires</span>
        </span>
      </div>
      <p className="muted small">* Years before {viirsStart} are estimated from MODIS by our harmonization model.</p>
    </div>
  );
}
