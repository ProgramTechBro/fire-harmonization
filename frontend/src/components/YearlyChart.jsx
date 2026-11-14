import { CartesianGrid, Legend, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt, RED, BLUE } from "../lib/format";

export default function YearlyChart({ yearly, viirsYear, height = 360 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={yearly} margin={{ top: 10, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#E6E6E6" />
        <ReferenceArea x1={yearly[0]?.year} x2={viirsYear} fill="#F2F2F2" fillOpacity={1} />
        <XAxis dataKey="year" tick={{ fontSize: 12, fill: "#6B6B6B" }} tickLine={false} axisLine={{ stroke: "#000" }} />
        <YAxis tick={{ fontSize: 12, fill: "#6B6B6B" }} tickLine={false} axisLine={false} tickFormatter={(v) => fmt(v)} width={72} />
        <Tooltip formatter={(v, n) => [fmt(v), n]} contentStyle={{ borderRadius: 0, border: "1px solid #000" }} />
        <Legend wrapperStyle={{ fontSize: 13, paddingTop: 8 }} iconType="plainline" />
        <Line dataKey="modis_raw" name="MODIS as recorded" stroke="#9A9A9A" strokeWidth={2} dot={false} />
        <Line dataKey="harmonized" name="Harmonized record" stroke={RED} strokeWidth={3} dot={false} />
        <Line dataKey="viirs" name="VIIRS as recorded" stroke="none" legendType="circle" dot={{ r: 4, fill: BLUE, stroke: "#fff", strokeWidth: 1.5 }} activeDot={{ r: 5, fill: BLUE }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
