import threading
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from . import config, geo, weather
from .store import Store


@asynccontextmanager
async def lifespan(app):
    app.state.store = Store(config.DATA_DIR, config.PRECOMPUTED_DIR)
    threading.Thread(target=app.state.store.model, daemon=True).start()
    yield


app = FastAPI(title="Emberlog API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_methods=["GET"], allow_headers=["*"])


def store():
    return app.state.store


def resolve_week(value):
    try:
        return store().snap_week(value)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e.args[0]))
    except ValueError:
        raise HTTPException(status_code=400, detail="Week must be a date like 2025-11-03")


@app.get("/api/health")
def health():
    s = store()
    return {"status": "ok", "cells": int(len(s.cells)), "latest_forecast_week": str(s.forecast_weeks[-1].date()),
            "weather_enabled": weather.enabled()}


@app.get("/api/meta")
def meta():
    out = store().meta()
    out["weather_enabled"] = weather.enabled()
    return out


@app.get("/api/cells")
def cells():
    return store().cells_payload()


@app.get("/api/forecast")
def forecast(week: Optional[str] = None, top: int = Query(15, ge=1, le=100)):
    return store().forecast_payload(resolve_week(week), top_n=top)


@app.get("/api/explain")
def explain(cell_id: int, week: Optional[str] = None):
    w = resolve_week(week)
    try:
        return store().explain(cell_id, w)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e.args[0]))


@app.get("/api/calendar")
def calendar_view(region: Optional[str] = None, lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                  lon_min: Optional[float] = None, lon_max: Optional[float] = None, cell_id: Optional[int] = None):
    s = store()
    try:
        ids, label = s.region_cells(region, lat_min, lat_max, lon_min, lon_max, cell_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e.args[0]))
    key = (region, lat_min, lat_max, lon_min, lon_max, cell_id)
    return s.calendar_payload(key, ids, label)


@app.get("/api/metrics")
def metrics():
    return store().metrics


@app.get("/api/weather")
async def weather_point(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
                        start: Optional[str] = None):
    if not weather.enabled():
        return {"available": False, "reason": "Weather service not configured"}
    try:
        d = date.fromisoformat(start) if start else datetime.now(timezone.utc).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="start must be a date like 2025-11-03")
    try:
        data = await weather.point_week(lat, lon, d)
    except weather.WeatherError as e:
        return {"available": False, "reason": str(e)}
    return {"available": True, "lat": lat, "lon": lon, "start": str(d), "source": "Meteomatics", **data}


@app.get("/api/smog")
async def smog(week: Optional[str] = None, city: str = "Lahore", radius_km: float = Query(400, ge=50, le=800)):
    target = geo.find_city(city)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Unknown city '{city}'")
    w = resolve_week(week)
    risky = store().smog_inputs(w, target, radius_km)

    wind_points = []
    wind_used = False
    note = None
    if weather.enabled():
        when = datetime(w.year, w.month, w.day, 9, tzinfo=timezone.utc) + timedelta(days=2)
        try:
            wind_points = await weather.wind_grid(target["lat"] + 4, target["lon"] - 4.5,
                                                  target["lat"] - 4, target["lon"] + 4.5, 0.5, when)
            wind_used = len(wind_points) > 0
        except weather.WeatherError as e:
            note = str(e)
    else:
        note = "Weather service not configured; estimate uses distance only"

    dist = risky["dist_km"].to_numpy()
    expected = risky["c"].to_numpy() * risky["p"].to_numpy()
    decay = np.exp(-dist / 250.0)
    if wind_used and len(risky):
        wl = np.array([p["lat"] for p in wind_points])
        wo = np.array([p["lon"] for p in wind_points])
        idx = np.argmin((risky["lat"].to_numpy()[:, None] - wl) ** 2 + (risky["lon"].to_numpy()[:, None] - wo) ** 2,
                        axis=1)
        speed = np.array([wind_points[i]["speed_ms"] for i in idx])
        travel = (np.array([wind_points[i]["dir_deg"] for i in idx]) + 180) % 360
        diff = np.abs((travel - risky["bearing_to_city"].to_numpy() + 180) % 360 - 180)
        align = np.where(diff <= 60, np.cos(np.radians(diff)), 0.0)
        reach = np.clip(speed * 86.4 / np.maximum(dist, 1), 0, 1)
        weight = align * np.maximum(reach, 0.3) * decay
    else:
        weight = 0.5 * decay
    contrib = expected * weight
    score = float(contrib.sum())
    if score < 30:
        level = "low"
    elif score < 150:
        level = "moderate"
    elif score < 500:
        level = "high"
    else:
        level = "very high"

    risky = risky.assign(contribution=contrib)
    top = risky[risky["contribution"] > 0].sort_values("contribution", ascending=False).head(10)
    return {
        "city": target,
        "week": str(w.date()),
        "level": level,
        "score": round(score, 1),
        "wind_used": wind_used,
        "note": note,
        "boxes_considered": int(len(risky)),
        "upwind_boxes": int((contrib > 0).sum()) if wind_used else None,
        "expected_fires_nearby": round(float(expected.sum()), 0),
        "sources": [{
            "cell_id": int(r.cell_id), "lat": round(float(r.lat), 3), "lon": round(float(r.lon), 3),
            "place": r.place, "dist_km": round(float(r.dist_km)), "p": round(float(r.p), 3),
            "expected": round(float(r.c), 1), "contribution": round(float(r.contribution), 2),
        } for r in top.itertuples()],
        "wind": wind_points,
        "method": "Indicative index: next-week fire forecast near the city, weighted by distance and by whether "
                  "the wind carries smoke toward the city. Not an air-quality measurement.",
    }


if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
