export const EMBER = ["#FFD37A", "#FF9B3D", "#FC3D21", "#8E1B0E"];
export const INK = "#000000";
export const SLATE = "#6B6B6B";
export const BLUE = "#0B3D91";
export const SKY = "#8DB8FF";
export const RED = "#FC3D21";
export const TEAL = BLUE;

export function fmt(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function pct(p) {
  if (p === null || p === undefined) return "–";
  if (p >= 0.995) return ">99%";
  if (p > 0 && p < 0.005) return "<1%";
  return `${Math.round(p * 100)}%`;
}

export function weekLabel(iso, withYear = true) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    timeZone: "UTC",
  });
}

export function addDays(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function weekRange(first, last) {
  const out = [];
  let w = first;
  while (w <= last) {
    out.push(w);
    w = addDays(w, 7);
  }
  return out;
}

function hexToRgb(h) {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const STOPS = EMBER.map(hexToRgb);

export function ember(t) {
  const x = Math.max(0, Math.min(1, t)) * (STOPS.length - 1);
  const i = Math.min(STOPS.length - 2, Math.floor(x));
  const f = x - i;
  const a = STOPS[i];
  const b = STOPS[i + 1];
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

export const LEVEL_COLOR = {
  low: "#A8A8A8",
  moderate: EMBER[0],
  high: EMBER[1],
  "very high": EMBER[2],
};

export function compassName(deg) {
  if (deg === null || deg === undefined) return "";
  const names = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];
  return names[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
}
