import { useEffect, useMemo, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Heatmap, { weekToDate, isoWeekOfMonthStart } from "../components/Heatmap";

const MONTH_TICKS = [0, 2, 4, 6, 8, 10].map((m) => isoWeekOfMonthStart(m));
const MONTH_NAMES = ["Jan", "Mar", "May", "Jul", "Sep", "Nov"];
import RegionPicker, { regionParams } from "../components/RegionPicker";
import PageHeader from "../components/PageHeader";
import { useApi } from "../lib/api";
import { fmt, weekLabel, EMBER, INK, SLATE } from "../lib/format";

function monthOf(year, w) {
  return weekToDate(year, w).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
}

function YearChart({ cal, year }) {
  const row = cal.heatmap.values[cal.heatmap.years.indexOf(year)] || [];
  const data = cal.climatology.map((c, i) => ({
    w: c.iso_week,
    month: monthOf(year, c.iso_week),
    year: row[i],
    avg: c.avg,
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={data} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#E6E6E6" />
        <XAxis
          dataKey="w"
          tick={{ fontSize: 11, fill: SLATE }}
          tickLine={false}
          axisLine={false}
          ticks={MONTH_TICKS}
          tickFormatter={(w) => MONTH_NAMES[MONTH_TICKS.indexOf(w)] || ""}
        />
        <YAxis tick={{ fontSize: 11, fill: SLATE }} tickLine={false} axisLine={false} tickFormatter={(v) => fmt(v)} width={56} />
        <Tooltip
          formatter={(v, n) => [fmt(v), n]}
          labelFormatter={(w) => `Week of ${weekToDate(year, w).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })}`}
        />
        <Area dataKey="year" name={`${year}`} stroke={EMBER[2]} fill={EMBER[2]} fillOpacity={0.14} strokeWidth={2} connectNulls />
        <Line dataKey="avg" name="Average year" stroke={INK} strokeDasharray="4 4" dot={false} strokeWidth={1.5} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export default function CalendarView({ meta, region, setRegion, selectedCell }) {
  const params = useMemo(() => regionParams(region), [region]);
  const { data: cal, error, loading } = useApi("calendar", params);
  const [year, setYear] = useState(2025);

  useEffect(() => {
    if (cal && !cal.heatmap.years.includes(year)) setYear(cal.heatmap.years[cal.heatmap.years.length - 1]);
  }, [cal]);

  const viirsYear = Number(meta.viirs_start.slice(0, 4));
  const yearTotal = cal?.yearly.find((y) => y.year === year);

  return (
    <>
      <PageHeader
        kicker="Burning activity calendar"
        title="When does burning happen?"
        aside={<RegionPicker regions={meta.regions} value={region} onChange={setRegion} selectedCell={selectedCell} dark />}
      >
        Every week since 2000, in one consistent unit: fires as the newer VIIRS satellite would count them. Pick an
        area to see its burning seasons, the weeks that broke the pattern, and how burning has changed.
      </PageHeader>

    <div className="page">
      {error && <p className="error">{error}</p>}
      {loading && !cal && <p className="muted">Building the calendar…</p>}

      {cal && (
        <div className="cal-grid">
          <section className="cal-main block">
            <h2>
              {cal.label}
              <span className="muted small"> {fmt(cal.boxes)} fire-prone boxes</span>
            </h2>
            <Heatmap heatmap={cal.heatmap} viirsStart={viirsYear} selectedYear={year} onYear={setYear} />

            <div className="year-head">
              <h2>{year} compared with an average year</h2>
              {yearTotal && (
                <span className="muted">
                  {fmt(yearTotal.harmonized)} fires in {year}
                  {year < viirsYear ? " (estimated)" : ""}
                </span>
              )}
            </div>
            <YearChart cal={cal} year={year} />
          </section>

          <aside className="cal-side">
            <section>
              <h2>When burning happens here</h2>
              {cal.critical_periods.length === 0 && <p className="muted">Too few fires to find a clear season.</p>}
              <ul className="periods">
                {cal.critical_periods.slice(0, 3).map((p) => (
                  <li key={p.start}>
                    <strong>
                      {p.start} to {p.end}
                    </strong>
                    <span>
                      {p.share_of_year_pct}% of the year's fires in {p.weeks} {p.weeks === 1 ? "week" : "weeks"}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            {cal.trend && (
              <section>
                <h2>Long-term trend</h2>
                <p>
                  {cal.trend.direction === "stable"
                    ? `Burning has stayed roughly level from ${cal.trend.from} to ${cal.trend.to}.`
                    : `Burning is ${cal.trend.direction}: about ${Math.abs(cal.trend.change_per_decade_pct)}% ${cal.trend.direction === "rising" ? "more" : "less"} per decade from ${cal.trend.from} to ${cal.trend.to}.`}
                </p>
              </section>
            )}

            <section>
              <h2>Unusually heavy weeks</h2>
              {cal.unusual_weeks.length === 0 ? (
                <p className="muted">No week stood far above its usual level.</p>
              ) : (
                <ul className="weeks-list">
                  {cal.unusual_weeks.slice(0, 6).map((u) => (
                    <li key={u.week}>
                      <span>{weekLabel(u.week)}</span>
                      <span>
                        {fmt(u.fires)} <span className="muted">vs usual {fmt(u.usual)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {cal.quiet_weeks.length > 0 && (
              <section>
                <h2>Quieter than usual in season</h2>
                <ul className="weeks-list">
                  {cal.quiet_weeks.slice(0, 4).map((u) => (
                    <li key={u.week}>
                      <span>{weekLabel(u.week)}</span>
                      <span>
                        {fmt(u.fires)} <span className="muted">vs usual {fmt(u.usual)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </aside>
        </div>
      )}
    </div>
    </>
  );
}
