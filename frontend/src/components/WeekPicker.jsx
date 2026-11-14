import { ChevronLeft, ChevronRight } from "lucide-react";
import { weekLabel } from "../lib/format";

export default function WeekPicker({ weeks, value, onChange, presets = [] }) {
  const i = Math.max(0, weeks.indexOf(value));
  const go = (k) => onChange(weeks[Math.max(0, Math.min(weeks.length - 1, k))]);

  return (
    <div className="week-picker">
      <div className="week-row">
        <button className="icon-btn" onClick={() => go(i - 1)} disabled={i === 0} aria-label="Previous week">
          <ChevronLeft size={18} />
        </button>
        <div className="week-label">
          <span className="muted">Forecast for the week of</span>
          <strong>{weekLabel(value)}</strong>
        </div>
        <button className="icon-btn" onClick={() => go(i + 1)} disabled={i === weeks.length - 1} aria-label="Next week">
          <ChevronRight size={18} />
        </button>
      </div>
      <input
        type="range"
        min={0}
        max={weeks.length - 1}
        value={i}
        onChange={(e) => go(Number(e.target.value))}
        aria-label="Choose forecast week"
        className="range"
      />
      <div className="range-ends muted">
        <span>{weekLabel(weeks[0])}</span>
        <span>{weekLabel(weeks[weeks.length - 1])}</span>
      </div>
      {presets.length > 0 && (
        <div className="chips">
          {presets.map((p) => (
            <button
              key={p.week}
              className={`chip ${p.week === value ? "chip-on" : ""}`}
              onClick={() => onChange(p.week)}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
