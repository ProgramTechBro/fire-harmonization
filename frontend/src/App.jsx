import { useEffect, useState } from "react";
import HomeView from "./views/HomeView";
import ForecastView from "./views/ForecastView";
import CalendarView from "./views/CalendarView";
import RecordView from "./views/RecordView";
import MethodView from "./views/MethodView";
import { useApi } from "./lib/api";

const TABS = [
  { id: "home", label: "Overview" },
  { id: "forecast", label: "Forecast map" },
  { id: "calendar", label: "Burning calendar" },
  { id: "record", label: "The record" },
  { id: "method", label: "Method" },
];

function useHashTab() {
  const read = () => {
    const h = window.location.hash.replace("#", "");
    return TABS.some((t) => t.id === h) ? h : "home";
  };
  const [tab, setTab] = useState(read);
  useEffect(() => {
    const on = () => setTab(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const go = (id) => {
    if (window.location.hash !== `#${id}`) window.location.hash = id;
    setTab(id);
    window.scrollTo(0, 0);
  };
  return [tab, go];
}

export function Mark({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect x="6" y="18" width="6" height="7" fill="#FFD37A" />
      <rect x="13" y="12" width="6" height="13" fill="#FF9B3D" />
      <rect x="20" y="6" width="6" height="19" fill="#FC3D21" />
    </svg>
  );
}

function pickStartWeek(meta) {
  const wanted = "2025-11-03";
  const { first, last } = meta.forecast_weeks;
  return wanted >= first && wanted <= last ? wanted : meta.latest_forecast_week;
}

export default function App() {
  const [tab, go] = useHashTab();
  const meta = useApi("meta", {});
  const cells = useApi("cells", {});
  const metrics = useApi("metrics", {});
  const [week, setWeek] = useState(null);
  const [selected, setSelected] = useState(null);
  const [region, setRegion] = useState("punjab_region");
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    if (meta.data && !week) setWeek(pickStartWeek(meta.data));
  }, [meta.data]);

  const navigate = (id) => {
    setMenu(false);
    go(id);
  };

  const openCalendar = (cellId) => {
    setRegion(`cell:${cellId}`);
    navigate("calendar");
  };

  const openBox = (cellId) => {
    setSelected(cellId);
    navigate("forecast");
  };

  const ready = meta.data && cells.data && week;

  return (
    <div className={`app tab-${tab}`}>
      <header className="topbar">
        <a
          className="brand"
          href="#home"
          onClick={(e) => {
            e.preventDefault();
            navigate("home");
          }}
        >
          <Mark />
          <span className="brand-text">
            <strong>Emberlog</strong>
            <span className="brand-sub">Satellite fire record for Pakistan and India</span>
          </span>
        </a>
        <button className="menu-btn" aria-expanded={menu} aria-controls="main-nav" onClick={() => setMenu(!menu)}>
          {menu ? "Close" : "Menu"}
        </button>
        <nav id="main-nav" aria-label="Sections" className={menu ? "open" : ""}>
          {TABS.map((t) => (
            <a
              key={t.id}
              href={`#${t.id}`}
              className={tab === t.id ? "active" : ""}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                navigate(t.id);
              }}
            >
              {t.label}
            </a>
          ))}
        </nav>
      </header>

      <main>
        {meta.error && (
          <div className="page">
            <h1 className="plain-title">The data server isn't responding</h1>
            <p className="muted">{meta.error} Refresh the page in a minute.</p>
          </div>
        )}
        {!meta.error && !ready && (
          <div className="boot">
            <Mark size={44} />
            <p>Loading 26 years of satellite fire data</p>
          </div>
        )}
        {ready && (
          <>
            {tab === "home" && (
              <HomeView
                meta={meta.data}
                cells={cells.data}
                metrics={metrics.data}
                heroWeek={pickStartWeek(meta.data)}
                go={navigate}
                openBox={openBox}
              />
            )}
            {tab === "forecast" && (
              <ForecastView
                meta={meta.data}
                cells={cells.data}
                week={week}
                setWeek={setWeek}
                selected={selected}
                setSelected={setSelected}
                openCalendar={openCalendar}
              />
            )}
            {tab === "calendar" && (
              <CalendarView meta={meta.data} region={region} setRegion={setRegion} selectedCell={selected} />
            )}
            {tab === "record" && (
              <RecordView
                meta={meta.data}
                metrics={metrics.data}
                region={region}
                setRegion={setRegion}
                selectedCell={selected}
              />
            )}
            {tab === "method" && <MethodView metrics={metrics.data} />}
          </>
        )}
      </main>

      {tab !== "forecast" && (
        <footer className="footer">
          <div className="footer-inner">
            <div className="footer-brand">
              <Mark size={26} />
              <strong>Emberlog</strong>
            </div>
            <p>
              Fire data from NASA FIRMS, MODIS Collection 6.1 and VIIRS S-NPP 375 m. Weather from Meteomatics. Map data
              from NASA GIBS (Black Marble), Esri and OpenStreetMap.
            </p>
            <p>Built by Waqar Ahmed, Zohaib Ahmed, Muhammad Hassan and Sakhi Ghulam for the NASA Space Apps Challenge 2026.</p>
          </div>
        </footer>
      )}
    </div>
  );
}
