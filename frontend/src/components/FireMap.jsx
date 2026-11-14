import { useEffect, useRef } from "react";
import L from "leaflet";
import { ember, pct, fmt, SKY, RED } from "../lib/format";

const HALF = 0.125;
const PUNJAB_VIEW = { center: [30.6, 74.4], zoom: 6 };
const ALL_BOUNDS = [[6.5, 61], [37.5, 97.5]];

export default function FireMap({ cells, forecast, selected, onSelect, smog, view, scrollZoom = true, initialView }) {
  const el = useRef(null);
  const map = useRef(null);
  const grid = useRef(null);
  const overlay = useRef(null);
  const rects = useRef([]);
  const values = useRef(new Map());
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  useEffect(() => {
    const m = L.map(el.current, {
      preferCanvas: true,
      zoomControl: false,
      minZoom: 4,
      maxZoom: 10,
      worldCopyJump: false,
      scrollWheelZoom: scrollZoom,
    }).setView((initialView || PUNJAB_VIEW).center, (initialView || PUNJAB_VIEW).zoom);
    L.control.zoom({ position: "bottomright" }).addTo(m);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      maxNativeZoom: 16,
      attribution: "Base map &copy; Esri, HERE, Garmin, OpenStreetMap contributors",
    }).addTo(m);
    L.tileLayer(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png",
      {
        maxNativeZoom: 8,
        opacity: 0.85,
        attribution: 'Night lights: <a href="https://earthdata.nasa.gov/gibs">NASA Black Marble, GIBS</a>',
      }
    ).addTo(m);
    m.createPane("labels");
    m.getPane("labels").style.zIndex = 450;
    m.getPane("labels").style.pointerEvents = "none";
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}", {
      maxNativeZoom: 16,
      pane: "labels",
    }).addTo(m);
    grid.current = L.layerGroup().addTo(m);
    overlay.current = L.layerGroup().addTo(m);
    map.current = m;
    return () => m.remove();
  }, []);

  useEffect(() => {
    if (!map.current || !view) return;
    if (view === "all") map.current.flyToBounds(ALL_BOUNDS, { duration: 0.8 });
    else map.current.flyTo(PUNJAB_VIEW.center, PUNJAB_VIEW.zoom, { duration: 0.8 });
  }, [view]);

  useEffect(() => {
    if (!cells || !map.current) return;
    grid.current.clearLayers();
    const renderer = L.canvas({ padding: 0.5 });
    rects.current = cells.cell_id.map((id, i) => {
      const la = cells.lat[i];
      const lo = cells.lon[i];
      const r = L.rectangle([[la - HALF, lo - HALF], [la + HALF, lo + HALF]], {
        renderer,
        stroke: false,
        fillColor: "#3d3d3d",
        fillOpacity: 0.1,
      });
      r.bindTooltip(() => {
        const v = values.current.get(id);
        const place = `${cells.place_km[i]} km from ${cells.place[i]}`;
        if (!v) return `<strong>${place}</strong>`;
        return `<strong>${place}</strong><br>${pct(v.p)} chance of fire<br>about ${fmt(v.c, v.c < 10 ? 1 : 0)} fires expected`;
      }, { sticky: true, direction: "top", className: "map-tip", offset: [0, -6] });
      r.on("click", () => selectRef.current(id));
      r.addTo(grid.current);
      return r;
    });
  }, [cells]);

  useEffect(() => {
    if (!cells || !forecast || !rects.current.length) return;
    const fc = forecast.cells;
    const next = new Map();
    fc.cell_id.forEach((id, i) => next.set(id, { p: fc.p[i], c: fc.expected[i] }));
    values.current = next;
    cells.cell_id.forEach((id, i) => {
      const v = next.get(id);
      const p = v ? v.p : 0;
      rects.current[i].setStyle({
        fillColor: p < 0.05 ? "#3d3d3d" : ember(p),
        fillOpacity: p < 0.05 ? 0.1 : 0.3 + 0.6 * p,
      });
    });
  }, [forecast, cells]);

  useEffect(() => {
    if (!overlay.current) return;
    overlay.current.clearLayers();
    if (smog && smog.city) {
      const city = [smog.city.lat, smog.city.lon];
      (smog.sources || []).slice(0, 6).forEach((s) => {
        L.polyline([[s.lat, s.lon], city], {
          color: SKY,
          weight: 1.5,
          opacity: 0.9,
          dashArray: "4 5",
          interactive: false,
        }).addTo(overlay.current);
      });
      (smog.wind || []).forEach((w, i) => {
        if (i % 2) return;
        const travel = (w.dir_deg + 180) % 360;
        L.marker([w.lat, w.lon], {
          interactive: false,
          icon: L.divIcon({
            className: "wind-arrow",
            html: `<span style="transform:rotate(${travel}deg)">&#x2191;</span>`,
            iconSize: [14, 14],
          }),
        }).addTo(overlay.current);
      });
      L.circleMarker(city, {
        radius: 7,
        color: "#ffffff",
        weight: 2,
        fillColor: RED,
        fillOpacity: 1,
      })
        .bindTooltip(smog.city.name, { permanent: true, direction: "right", className: "city-tip", offset: [8, 0] })
        .addTo(overlay.current);
    }
    if (selected && cells) {
      const i = cells.cell_id.indexOf(selected);
      if (i >= 0) {
        const la = cells.lat[i];
        const lo = cells.lon[i];
        L.rectangle([[la - HALF, lo - HALF], [la + HALF, lo + HALF]], {
          color: "#ffffff",
          weight: 2.5,
          fill: false,
          interactive: false,
        }).addTo(overlay.current);
      }
    }
  }, [smog, selected, cells]);

  return <div ref={el} className="map" role="application" aria-label="Map of next-week fire risk" />;
}
