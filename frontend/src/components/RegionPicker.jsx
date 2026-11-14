export default function RegionPicker({ regions, value, onChange, selectedCell, dark = false }) {
  return (
    <label className={`region-picker ${dark ? "on-dark" : ""}`}>
      <span>Area</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {regions.map((r) => (
          <option key={r.id} value={r.id}>
            {r.label}
          </option>
        ))}
        {selectedCell && <option value={`cell:${selectedCell}`}>The box you selected on the map</option>}
      </select>
    </label>
  );
}

export function regionParams(value) {
  if (value.startsWith("cell:")) return { cell_id: value.slice(5) };
  return { region: value };
}
