import time
from datetime import datetime, timedelta, timezone
import httpx
from . import config

BASE_URL = "https://api.meteomatics.com"
POINT_PARAMS = "t_max_2m_24h:C,t_min_2m_24h:C,precip_24h:mm,wind_speed_10m:ms,wind_dir_10m:d,relative_humidity_2m:p"
_cache = {}


class WeatherError(Exception):
    pass


def enabled():
    return bool(config.METEOMATICS_USERNAME and config.METEOMATICS_PASSWORD)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _get(path):
    now = time.time()
    hit = _cache.get(path)
    if hit and now - hit[0] < config.WEATHER_CACHE_SECONDS:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=20, auth=(config.METEOMATICS_USERNAME, config.METEOMATICS_PASSWORD)) as client:
            r = await client.get(f"{BASE_URL}/{path}")
    except httpx.HTTPError as e:
        raise WeatherError(f"Weather service unreachable: {e}") from e
    if r.status_code != 200:
        raise WeatherError(f"Weather service returned {r.status_code}: {r.text[:200]}")
    data = r.json()
    _cache[path] = (now, data)
    return data


def _series(data):
    out = {}
    for block in data.get("data", []):
        name = block["parameter"].split(":")[0]
        for coord in block.get("coordinates", []):
            key = (round(coord["lat"], 4), round(coord["lon"], 4))
            out.setdefault(key, {})[name] = [(d["date"], d["value"]) for d in coord.get("dates", [])]
    return out


def _clean(v):
    return None if v is None or v <= -666 else round(float(v), 2)


async def point_week(lat, lon, start):
    s = datetime(start.year, start.month, start.day, 12, tzinfo=timezone.utc)
    e = s + timedelta(days=6)
    path = f"{iso(s)}--{iso(e)}:P1D/{POINT_PARAMS}/{lat:.3f},{lon:.3f}/json"
    series = _series(await _get(path))
    if not series:
        raise WeatherError("No weather data returned")
    values = next(iter(series.values()))
    days = []
    for i, (date, _) in enumerate(values.get("t_max_2m_24h", [])):
        def pick(name):
            arr = values.get(name, [])
            return _clean(arr[i][1]) if i < len(arr) else None
        days.append({
            "date": date[:10],
            "t_max": pick("t_max_2m_24h"),
            "t_min": pick("t_min_2m_24h"),
            "precip_mm": pick("precip_24h"),
            "wind_speed_ms": pick("wind_speed_10m"),
            "wind_dir_deg": pick("wind_dir_10m"),
            "humidity_pct": pick("relative_humidity_2m"),
        })
    rain = sum(d["precip_mm"] or 0 for d in days)
    hums = [d["humidity_pct"] for d in days if d["humidity_pct"] is not None]
    winds = [d["wind_speed_ms"] for d in days if d["wind_speed_ms"] is not None]
    humidity = sum(hums) / len(hums) if hums else None
    max_wind = max(winds) if winds else None
    if rain >= 10:
        burn = "wet"
    elif rain < 2 and humidity is not None and humidity < 60:
        burn = "dry"
    else:
        burn = "mixed"
    return {
        "days": days,
        "summary": {
            "total_rain_mm": round(rain, 1),
            "mean_humidity_pct": round(humidity, 1) if humidity is not None else None,
            "max_wind_ms": max_wind,
            "burning_conditions": burn,
            "spread_risk": "high" if max_wind is not None and max_wind >= 6 else "normal",
        },
    }


async def wind_grid(lat_max, lon_min, lat_min, lon_max, res, when):
    path = (f"{iso(when)}/wind_speed_10m:ms,wind_dir_10m:d/"
            f"{lat_max:.2f},{lon_min:.2f}_{lat_min:.2f},{lon_max:.2f}:{res},{res}/json")
    series = _series(await _get(path))
    points = []
    for (la, lo), vals in series.items():
        sp = vals.get("wind_speed_10m", [(None, None)])[0][1]
        di = vals.get("wind_dir_10m", [(None, None)])[0][1]
        if sp is None or di is None or sp <= -666 or di <= -666:
            continue
        points.append({"lat": la, "lon": lo, "speed_ms": round(float(sp), 2), "dir_deg": round(float(di), 1)})
    return points
