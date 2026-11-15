import calendar
import json
import threading
from collections import OrderedDict
from pathlib import Path
import numpy as np
import pandas as pd
from . import geo

VIIRS_START = pd.Timestamp("2012-01-16")
AQUA_START = pd.Timestamp("2002-07-01")

LABELS = {
    "h_now": "Fires in this box this week",
    "h_lag1": "Fires 1 week ago",
    "h_lag2": "Fires 2 weeks ago",
    "h_lag3": "Fires 3 weeks ago",
    "h_roll4": "Average fires, last 4 weeks",
    "h_roll12": "Average fires, last 12 weeks",
    "nb_now": "Fires in nearby boxes this week",
    "nb_roll4": "Nearby fires, last 4 weeks",
    "h_lastyear": "Fires same week last year",
    "nb_lastyear": "Nearby fires same week last year",
    "h_clim5": "5-year average for this week",
    "h_cummean": "Long-term fire rate of this box",
    "lat": "Location (latitude)",
    "lon": "Location (longitude)",
    "woy": "Time of year (week)",
    "month": "Time of year (month)",
}

SENTENCES = {
    "h_now": "it already has {v:.0f} fires this week",
    "h_lag1": "it had {v:.0f} fires one week ago",
    "h_lag2": "it had {v:.0f} fires two weeks ago",
    "h_lag3": "it had {v:.0f} fires three weeks ago",
    "h_roll4": "it averaged {v:.1f} fires per week over the last month",
    "h_roll12": "it averaged {v:.1f} fires per week over the last three months",
    "nb_now": "nearby boxes have {v:.0f} fires this week",
    "nb_roll4": "nearby boxes averaged {v:.0f} fires per week over the last month",
    "h_lastyear": "it had about {v:.0f} fires around this week last year",
    "nb_lastyear": "nearby boxes had about {v:.0f} fires around this week last year",
    "h_clim5": "over the past 5 years it averaged {v:.0f} fires in this week",
    "h_cummean": "its long-term average is {v:.1f} fires per week",
    "lat": "its location",
    "lon": "its location",
    "woy": "the time of year (week {v:.0f})",
    "month": "the time of year ({m})",
}


def risk_level(p, threshold):
    if p >= max(0.75, threshold):
        return "very high"
    if p >= threshold:
        return "high"
    if p >= threshold / 2:
        return "moderate"
    return "low"


def _f(x, nd=3):
    if x is None:
        return None
    x = float(x)
    if np.isnan(x):
        return None
    return round(x, nd)


class Store:
    def __init__(self, data_dir, bundle_dir):
        data_dir = Path(data_dir)
        bundle = Path(bundle_dir)
        if not (bundle / "meta.json").exists():
            from .precompute import build_bundle
            build_bundle(data_dir, bundle)
        self.data_dir = data_dir
        self.bundle = bundle
        meta = json.loads((bundle / "meta.json").read_text())
        self.features = meta["features"]
        self.threshold = float(meta["threshold"])
        self.metrics = meta.get("metrics", {})
        self.forecast_weeks = pd.DatetimeIndex(pd.to_datetime(meta["forecast_weeks"]))
        self.all_weeks = pd.date_range(meta["calendar_first"], periods=int(meta["calendar_weeks"]), freq="W-MON")
        self.cal_first = self.all_weeks[0]

        cells = pd.DataFrame(json.loads((bundle / "cells.json").read_text()))
        cells["cell_id"] = cells["cell_id"].astype("int32")
        names, dist = geo.nearest_cities(cells["lat"], cells["lon"])
        cells["place"] = names
        cells["place_km"] = np.round(dist).astype(int)
        self.cells = cells.sort_values("cell_id").reset_index(drop=True)
        ids = self.cells["cell_id"].to_numpy()
        self.pos_lookup = np.full(int(ids.max()) + 1, -1, dtype="int32")
        self.pos_lookup[ids] = np.arange(len(ids), dtype="int32")

        def arr(name):
            return np.load(bundle / f"{name}.npy", mmap_mode="r")

        self.fx, self.fcell, self.fwk = arr("fx"), arr("fcell"), arr("fwk")
        self.fy, self.fp, self.fc = arr("fy"), arr("fp"), arr("fc")
        self.ccell, self.cwk, self.ch, self.cm, self.cv = arr("ccell"), arr("cwk"), arr("ch"), arr("cm"), arr("cv")
        wk = np.arange(len(self.forecast_weeks))
        starts = np.searchsorted(self.fwk, wk, side="left")
        ends = np.searchsorted(self.fwk, wk, side="right")
        self.week_slices = {w: (int(a), int(b)) for w, a, b in zip(self.forecast_weeks, starts, ends)}

        self._model = None
        self._model_lock = threading.Lock()
        self._forecast_cache = OrderedDict()
        self._calendar_cache = OrderedDict()
        self._calendar_fixed = {}
        for f in (bundle / "calendars").glob("*.json"):
            self._calendar_fixed[f.stem] = json.loads(f.read_text())

    def model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    import lightgbm as lgb
                    self._model = lgb.Booster(model_file=str(self.bundle / "forecast_fire_prob.txt"))
        return self._model

    def position(self, cell_id):
        if 0 <= cell_id < len(self.pos_lookup) and self.pos_lookup[cell_id] >= 0:
            return int(self.pos_lookup[cell_id])
        raise KeyError(f"Unknown cell_id {cell_id}")

    def snap_week(self, value):
        if value is None:
            return self.forecast_weeks[-1]
        d = pd.Timestamp(value).normalize()
        monday = d - pd.Timedelta(days=d.dayofweek)
        if monday not in self.week_slices:
            raise KeyError(
                f"No forecast for week {monday.date()}. Available: "
                f"{self.forecast_weeks[0].date()} to {self.forecast_weeks[-1].date()}"
            )
        return monday

    def meta(self):
        return {
            "forecast_weeks": {"first": str(self.forecast_weeks[0].date()), "last": str(self.forecast_weeks[-1].date()),
                               "count": len(self.forecast_weeks)},
            "latest_forecast_week": str(self.forecast_weeks[-1].date()),
            "calendar_weeks": {"first": str(self.all_weeks[0].date()), "last": str(self.all_weeks[-1].date()),
                               "count": len(self.all_weeks)},
            "viirs_start": str(VIIRS_START.date()),
            "aqua_start": str(AQUA_START.date()),
            "threshold": round(self.threshold, 4),
            "cells": {"total": int(len(self.cells)),
                      "pakistan": int((self.cells["country"] == "Pakistan").sum()),
                      "india": int((self.cells["country"] == "India").sum())},
            "grid_deg": 0.25,
            "regions": [{"id": k, "label": v["label"]} for k, v in geo.REGIONS.items()],
            "smog_cities": geo.SMOG_CITIES,
        }

    def cells_payload(self):
        c = self.cells
        return {
            "cell_id": c["cell_id"].tolist(),
            "lat": np.round(c["lat"], 3).tolist(),
            "lon": np.round(c["lon"], 3).tolist(),
            "country": c["country"].tolist(),
            "punjab": c["punjab"].astype(int).tolist(),
            "place": c["place"].tolist(),
            "place_km": c["place_km"].tolist(),
        }

    def forecast(self, week):
        if week in self._forecast_cache:
            self._forecast_cache.move_to_end(week)
            return self._forecast_cache[week]
        s, e = self.week_slices[week]
        pos = self.pos_lookup[np.asarray(self.fcell[s:e], dtype="int64")]
        info = self.cells.iloc[pos].reset_index(drop=True)
        df = pd.DataFrame({
            "cell_id": info["cell_id"].to_numpy(),
            "p": np.asarray(self.fp[s:e], dtype="float64"),
            "c": np.asarray(self.fc[s:e], dtype="float64"),
            "actual": np.asarray(self.fy[s:e], dtype="float64"),
        })
        for col in ["lat", "lon", "country", "punjab", "place", "place_km"]:
            df[col] = info[col].to_numpy()
        self._forecast_cache[week] = df
        if len(self._forecast_cache) > 24:
            self._forecast_cache.popitem(last=False)
        return df

    def forecast_payload(self, week, top_n=15):
        df = self.forecast(week)
        has_actual = bool(df["actual"].notna().any())
        high = df["p"] >= self.threshold
        pj = df["punjab"] == 1
        top = df.sort_values("p", ascending=False).head(top_n)
        actual = df["actual"].to_numpy()
        return {
            "week": str(week.date()),
            "threshold": round(self.threshold, 4),
            "has_actual": has_actual,
            "cells": {
                "cell_id": df["cell_id"].tolist(),
                "p": np.round(df["p"].to_numpy(), 4).tolist(),
                "expected": np.round(df["c"].to_numpy(), 2).tolist(),
                "actual": [None if np.isnan(a) else round(float(a), 1) for a in actual],
            },
            "summary": {
                "high_risk_boxes": int(high.sum()),
                "high_risk_pakistan": int((high & (df["country"] == "Pakistan")).sum()),
                "high_risk_india": int((high & (df["country"] == "India")).sum()),
                "expected_fires": round(float(df["c"].sum()), 0),
                "expected_fires_punjab": round(float(df.loc[pj, "c"].sum()), 0),
                "actual_fires": round(float(np.nansum(actual)), 0) if has_actual else None,
                "actual_fires_punjab": round(float(np.nansum(actual[pj.to_numpy()])), 0) if has_actual else None,
            },
            "top": [{
                "cell_id": int(r.cell_id), "lat": _f(r.lat), "lon": _f(r.lon), "country": r.country,
                "place": r.place, "place_km": int(r.place_km), "p": _f(r.p, 4), "expected": _f(r.c, 1),
                "actual": _f(r.actual, 1), "level": risk_level(r.p, self.threshold),
            } for r in top.itertuples()],
        }

    def _contributions(self, x):
        out = np.asarray(self.model().predict(x, pred_contrib=True))[0]
        return out[:-1], float(out[-1])

    def _sentence(self, name, value):
        tpl = SENTENCES.get(name, LABELS.get(name, name))
        if name == "month":
            return tpl.format(m=calendar.month_name[int(value)] if 1 <= int(value) <= 12 else value)
        try:
            return tpl.format(v=float(value))
        except (ValueError, TypeError):
            return tpl

    def explain(self, cell_id, week):
        pos = self.position(cell_id)
        s, e = self.week_slices[week]
        ids = self.fcell[s:e]
        i = int(np.searchsorted(ids, cell_id))
        if i >= len(ids) or ids[i] != cell_id:
            raise KeyError(f"No data for cell {cell_id} in week {week.date()}")
        r = s + i
        values = np.asarray(self.fx[r], dtype="float64")
        contribs, base_value = self._contributions(values.reshape(1, -1))
        p = float(self.fp[r])
        c = float(self.fc[r])
        order = np.argsort(-np.abs(contribs))
        factors = [{
            "feature": self.features[j],
            "label": LABELS.get(self.features[j], self.features[j]),
            "value": _f(values[j], 2),
            "contribution": round(float(contribs[j]), 4),
            "direction": "up" if contribs[j] > 0 else "down",
        } for j in order]
        ups = [self._sentence(self.features[j], values[j]) for j in order if contribs[j] > 0][:3]
        downs = [self._sentence(self.features[j], values[j]) for j in order if contribs[j] < 0][:2]
        level = risk_level(p, self.threshold)
        text = f"{level.capitalize()} risk"
        if ups:
            text += " mainly because " + (", ".join(ups[:-1]) + " and " + ups[-1] if len(ups) > 1 else ups[0])
        text += "."
        if downs and level in ("low", "moderate"):
            text += " Risk is held down because " + " and ".join(downs) + "."
        cell = self.cells.iloc[pos]
        actual = float(self.fy[r])
        return {
            "cell_id": int(cell_id),
            "week": str(week.date()),
            "lat": _f(cell["lat"]), "lon": _f(cell["lon"]),
            "country": cell["country"], "place": cell["place"], "place_km": int(cell["place_km"]),
            "probability": round(p, 4),
            "expected_fires": round(c, 1),
            "actual_fires": _f(actual, 1),
            "level": level,
            "threshold": round(self.threshold, 4),
            "base_value": round(base_value, 4),
            "summary": text,
            "factors": factors,
            "history": self.cell_history(cell_id, week),
        }

    def _cell_rows(self, cell_id):
        a = int(np.searchsorted(self.ccell, cell_id, side="left"))
        b = int(np.searchsorted(self.ccell, cell_id, side="right"))
        return a, b

    def cell_history(self, cell_id, week, weeks_back=16):
        a, b = self._cell_rows(cell_id)
        dense = np.zeros(len(self.all_weeks), dtype="float64")
        dense[np.asarray(self.cwk[a:b], dtype="int64")] = np.asarray(self.ch[a:b], dtype="float64")
        idx = pd.date_range(week - pd.Timedelta(weeks=weeks_back), week + pd.Timedelta(weeks=4), freq="W-MON")

        def take(dates):
            k = ((dates - self.cal_first).days // 7).to_numpy()
            ok = (k >= 0) & (k < len(dense))
            out = np.zeros(len(k))
            out[ok] = dense[k[ok]]
            return out

        this_year = take(idx)
        last_year = take(idx - pd.Timedelta(weeks=52))
        return [{
            "week": str(w.date()),
            "fires": None if w > self.all_weeks[-1] else round(float(x), 1),
            "last_year": round(float(y), 1),
            "is_target": bool(w == week),
        } for w, x, y in zip(idx, this_year, last_year)]

    def region_cells(self, region=None, lat_min=None, lat_max=None, lon_min=None, lon_max=None, cell_id=None):
        c = self.cells
        if cell_id is not None:
            pos = self.position(cell_id)
            row = c.iloc[pos]
            return np.array([cell_id]), f"Box near {row['place']} ({row['lat']:.2f}, {row['lon']:.2f})"
        if None not in (lat_min, lat_max, lon_min, lon_max):
            m = c["lat"].between(lat_min, lat_max) & c["lon"].between(lon_min, lon_max)
            label = f"Custom area ({lat_min:.2f} to {lat_max:.2f}N, {lon_min:.2f} to {lon_max:.2f}E)"
        else:
            region = region or "punjab_region"
            spec = geo.REGIONS.get(region)
            if spec is None:
                raise KeyError(f"Unknown region '{region}'")
            m = pd.Series(True, index=c.index)
            if "bbox" in spec:
                a, b, x, y = spec["bbox"]
                m &= c["lat"].between(a, b) & c["lon"].between(x, y)
            if "country" in spec:
                m &= c["country"] == spec["country"]
            label = spec["label"]
        ids = c.loc[m, "cell_id"].to_numpy()
        if len(ids) == 0:
            raise KeyError("No fire-prone boxes in this area")
        return ids, label

    def calendar_payload(self, key, ids, label):
        region = key[0] if all(k is None for k in key[1:]) else None
        if region in self._calendar_fixed:
            return self._calendar_fixed[region]
        if key in self._calendar_cache:
            return self._calendar_cache[key]
        n = len(self.all_weeks)
        if len(ids) == 1:
            a, b = self._cell_rows(int(ids[0]))
            sel = slice(a, b)
        else:
            sel = np.isin(self.ccell, np.asarray(ids, dtype=self.ccell.dtype))
        wk = np.asarray(self.cwk[sel], dtype="int64")
        h = np.bincount(wk, weights=np.asarray(self.ch[sel], dtype="float64"), minlength=n)
        m = np.bincount(wk, weights=np.asarray(self.cm[sel], dtype="float64"), minlength=n)
        v = np.bincount(wk, weights=np.nan_to_num(np.asarray(self.cv[sel], dtype="float64")), minlength=n)
        g = pd.DataFrame({"h": h, "m": m, "v": v}, index=self.all_weeks)
        g.loc[g.index < VIIRS_START, "v"] = np.nan
        iso = g.index.isocalendar()
        g["iso_year"] = iso["year"].to_numpy().astype(int)
        g["iso_week"] = iso["week"].to_numpy().astype(int)

        stats = g.groupby("iso_week")["h"].agg(["mean", "std"])
        g = g.join(stats, on="iso_week")
        g["z"] = np.where(g["std"] > 0, (g["h"] - g["mean"]) / g["std"], 0.0)

        weekly = [{
            "week": str(w.date()),
            "harmonized": round(float(r.h), 1),
            "modis_raw": int(r.m),
            "viirs": None if np.isnan(r.v) else round(float(r.v), 1),
            "estimated": bool(w < VIIRS_START),
            "z": round(float(r.z), 2),
        } for w, r in zip(g.index, g.itertuples())]

        years = sorted(g["iso_year"].unique().tolist())
        heat = np.full((len(years), 53), None, dtype=object)
        yi = {y: i for i, y in enumerate(years)}
        for y, wk, h in zip(g["iso_year"], g["iso_week"], g["h"]):
            heat[yi[y], wk - 1] = round(float(h), 1)

        clim = stats["mean"].reindex(range(1, 54)).fillna(0)
        peak = float(clim.max()) if len(clim) else 0.0
        periods = []
        if peak > 0:
            hot = clim >= 0.4 * peak
            run = []
            for wk, flag in hot.items():
                if flag:
                    run.append(wk)
                elif run:
                    periods.append(run)
                    run = []
            if run:
                periods.append(run)
            annual = float(clim.sum())
            ref = 2025
            periods = sorted([{
                "start": str(pd.Timestamp.fromisocalendar(ref, min(p[0], 52), 1).strftime("%d %b")),
                "end": str((pd.Timestamp.fromisocalendar(ref, min(p[-1], 52), 1) + pd.Timedelta(days=6)).strftime("%d %b")),
                "weeks": len(p),
                "share_of_year_pct": round(100 * float(clim.loc[p].sum()) / annual, 1) if annual else 0,
                "peak_week_avg": round(float(clim.loc[p].max()), 1),
            } for p in periods], key=lambda d: -d["share_of_year_pct"])

        yearly = g.groupby(g.index.year).agg(h=("h", "sum"), m=("m", "sum"), v=("v", lambda s: s.sum(min_count=1)))
        yearly = yearly.loc[2001:]
        trend = None
        fit = yearly.loc[2003:]
        if len(fit) >= 5 and fit["h"].mean() > 0:
            slope = np.polyfit(fit.index.to_numpy(dtype=float), fit["h"].to_numpy(dtype=float), 1)[0]
            trend = {"from": int(fit.index.min()), "to": int(fit.index.max()),
                     "change_per_decade_pct": round(float(slope * 10 / fit["h"].mean() * 100), 1),
                     "direction": "stable"}
            pct = trend["change_per_decade_pct"]
            if pct >= 5:
                trend["direction"] = "rising"
            elif pct <= -5:
                trend["direction"] = "falling"

        unusual = g[(g["z"] >= 2.5) & (g["h"] >= max(5.0, 0.1 * peak))].sort_values("z", ascending=False).head(12)
        quiet = g[(g["z"] <= -1.5) & (g["mean"] >= 0.4 * peak) & (g["mean"] > 0)].sort_values("z").head(6)

        payload = {
            "label": label,
            "boxes": int(len(ids)),
            "weekly": weekly,
            "heatmap": {"years": years, "weeks": list(range(1, 54)), "values": heat.tolist()},
            "climatology": [{"iso_week": int(w), "avg": round(float(v), 1)} for w, v in clim.items()],
            "critical_periods": periods,
            "unusual_weeks": [{"week": str(w.date()), "fires": round(float(r.h), 1), "usual": round(float(r.mean), 1),
                               "z": round(float(r.z), 2)} for w, r in zip(unusual.index, unusual.itertuples())],
            "quiet_weeks": [{"week": str(w.date()), "fires": round(float(r.h), 1), "usual": round(float(r.mean), 1),
                             "z": round(float(r.z), 2)} for w, r in zip(quiet.index, quiet.itertuples())],
            "yearly": [{"year": int(y), "harmonized": round(float(r.h), 0), "modis_raw": int(r.m),
                        "viirs": None if np.isnan(r.v) else round(float(r.v), 0)}
                       for y, r in zip(yearly.index, yearly.itertuples())],
            "trend": trend,
        }
        self._calendar_cache[key] = payload
        if len(self._calendar_cache) > 32:
            self._calendar_cache.popitem(last=False)
        return payload

    def smog_inputs(self, week, city, radius_km=400):
        df = self.forecast(week)
        d = geo.haversine_km(df["lat"].to_numpy(), df["lon"].to_numpy(), city["lat"], city["lon"])
        m = (d <= radius_km) & (d >= 10) & (df["p"].to_numpy() >= self.threshold / 2)
        risky = df.loc[m].copy()
        risky["dist_km"] = d[m]
        risky["bearing_to_city"] = geo.bearing_deg(risky["lat"].to_numpy(), risky["lon"].to_numpy(),
                                                   city["lat"], city["lon"])
        return risky
