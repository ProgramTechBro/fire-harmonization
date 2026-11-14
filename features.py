import numpy as np
import pandas as pd
from scipy import sparse

GRID = 0.25
HISTORY = 259
PUNJAB = {"lat_min": 28.0, "lat_max": 34.0, "lon_min": 69.5, "lon_max": 77.5}

F_FULL = ["m_count", "m_aqua", "m_terra", "m_frp_sum", "m_frp_max", "m_bright_mean", "m_day",
          "m_prev", "m_next", "cell_m_mean", "cell_t_mean", "cell_woy_t_mean", "lat", "lon", "woy", "month"]
F_TERRA = ["m_terra", "t_prev", "t_next", "cell_t_mean", "cell_woy_t_mean", "lat", "lon", "woy", "month"]
FORECAST_FEATS = ["h_now", "h_lag1", "h_lag2", "h_lag3", "h_roll4", "h_roll12", "nb_now", "nb_roll4",
                  "h_lastyear", "nb_lastyear", "h_clim5", "h_cummean", "lat", "lon", "woy", "month"]

NICE = {
    "m_count": "MODIS fires (total)",
    "m_aqua": "MODIS Aqua fires",
    "m_terra": "MODIS Terra fires",
    "m_frp_sum": "MODIS total fire power",
    "m_frp_max": "MODIS strongest fire",
    "m_bright_mean": "MODIS avg brightness",
    "m_day": "MODIS daytime fires",
    "m_prev": "MODIS fires previous week",
    "m_next": "MODIS fires following week",
    "t_prev": "Terra fires previous week",
    "t_next": "Terra fires following week",
    "cell_m_mean": "Box long-term MODIS rate",
    "cell_t_mean": "Box long-term Terra rate",
    "cell_woy_t_mean": "Box usual Terra fires this week",
    "h_now": "Fires in box this week",
    "h_lag1": "Fires 1 week ago",
    "h_lag2": "Fires 2 weeks ago",
    "h_lag3": "Fires 3 weeks ago",
    "h_roll4": "Avg fires last 4 weeks",
    "h_roll12": "Avg fires last 12 weeks",
    "nb_now": "Fires in nearby boxes this week",
    "nb_roll4": "Nearby fires last 4 weeks",
    "h_lastyear": "Fires same week last year",
    "nb_lastyear": "Nearby fires same week last year",
    "h_clim5": "5-year average for this week",
    "h_cummean": "Box long-term fire rate",
    "lat": "Latitude",
    "lon": "Longitude",
    "woy": "Week of year",
    "month": "Month",
}


def in_punjab(lat, lon):
    return (lat.between(PUNJAB["lat_min"], PUNJAB["lat_max"]) & lon.between(PUNJAB["lon_min"], PUNJAB["lon_max"])).astype("int8")


def add_harmonize_features(df):
    df = df.sort_values(["cell_id", "week"]).reset_index(drop=True)
    df["m_aqua"] = df["m_count"] - df["m_terra"]
    g = df.groupby("cell_id")
    df["m_prev"] = g["m_count"].shift(1).fillna(0)
    df["m_next"] = g["m_count"].shift(-1).fillna(0)
    df["t_prev"] = g["m_terra"].shift(1).fillna(0)
    df["t_next"] = g["m_terra"].shift(-1).fillna(0)
    df["cell_t_mean"] = g["m_terra"].transform("mean")
    df["cell_woy_t_mean"] = df.groupby(["cell_id", "woy"])["m_terra"].transform("mean")
    cell_m_mean = df[df["aqua_on"] == 1].groupby("cell_id")["m_count"].mean()
    df["cell_m_mean"] = df["cell_id"].map(cell_m_mean).fillna(0)
    df["punjab"] = in_punjab(df["lat"], df["lon"])
    return df


def lag(X, k):
    out = np.full_like(X, np.nan)
    out[:, k:] = X[:, :-k]
    return out


def roll(X, k):
    cs = np.cumsum(X, axis=1, dtype="float64")
    out = cs.copy()
    out[:, k:] = cs[:, k:] - cs[:, :-k]
    out[:, :k - 1] = np.nan
    return (out / k).astype("float32")


def mean_of(arrs):
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return np.nanmean(np.stack(arrs), axis=0).astype("float32")


def neighbour_matrix(cells):
    li = np.round((cells["lat"].to_numpy() - GRID / 2) / GRID).astype(int)
    lo = np.round((cells["lon"].to_numpy() - GRID / 2) / GRID).astype(int)
    pos = {(a, b): i for i, (a, b) in enumerate(zip(li, lo))}
    r, c = [], []
    for i, (a, b) in enumerate(zip(li, lo)):
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                if da == 0 and db == 0:
                    continue
                j = pos.get((a + da, b + db))
                if j is not None:
                    r.append(i)
                    c.append(j)
    n = len(cells)
    return sparse.csr_matrix((np.ones(len(r), dtype="float32"), (r, c)), shape=(n, n))


def forecast_inputs(df):
    df = df.sort_values(["cell_id", "week"]).reset_index(drop=True)
    cells = df.groupby("cell_id", sort=True).agg(
        lat=("lat", "first"), lon=("lon", "first"), punjab=("punjab", "first"), country=("country", "first")
    ).reset_index()
    weeks = pd.DatetimeIndex(np.sort(df["week"].unique()))
    C, W = len(cells), len(weeks)
    H = df["h_count"].to_numpy(dtype="float32").reshape(C, W)
    if "v_count" in df:
        V = df["v_count"].to_numpy(dtype="float32").reshape(C, W)
    else:
        V = np.full((C, W), np.nan, dtype="float32")
    NB = np.asarray(neighbour_matrix(cells) @ H, dtype="float32")
    F = {
        "h_now": H,
        "h_lag1": lag(H, 1),
        "h_lag2": lag(H, 2),
        "h_lag3": lag(H, 3),
        "h_roll4": roll(H, 4),
        "h_roll12": roll(H, 12),
        "nb_now": NB,
        "nb_roll4": roll(NB, 4),
        "h_lastyear": mean_of([lag(H, 50), lag(H, 51), lag(H, 52)]),
        "nb_lastyear": mean_of([lag(NB, 50), lag(NB, 51), lag(NB, 52)]),
        "h_clim5": mean_of([lag(H, 52 * k - 1) for k in range(1, 6)]),
        "h_cummean": (np.cumsum(H, axis=1, dtype="float64") / np.arange(1, W + 1)).astype("float32"),
    }
    return {"cells": cells, "weeks": weeks, "F": F, "V": V}


def build_rows(inp, ts):
    cells, weeks, F, V = inp["cells"], inp["weeks"], inp["F"], inp["V"]
    C, W = len(cells), len(weeks)
    ts = np.asarray(ts)
    n = len(ts)
    tw = weeks[ts] + pd.Timedelta(days=7)
    out = {name: arr[:, ts].ravel() for name, arr in F.items()}
    out["cell_id"] = np.repeat(cells["cell_id"].to_numpy(), n)
    out["lat"] = np.repeat(cells["lat"].to_numpy(), n)
    out["lon"] = np.repeat(cells["lon"].to_numpy(), n)
    out["punjab"] = np.repeat(cells["punjab"].to_numpy(), n)
    out["country"] = np.repeat(cells["country"].astype(str).to_numpy(), n)
    out["target_week"] = np.tile(tw.values, C)
    out["woy"] = np.tile(tw.isocalendar().week.to_numpy().astype("int8"), C)
    out["month"] = np.tile(tw.month.to_numpy().astype("int8"), C)
    nxt = np.minimum(ts + 1, W - 1)
    y = V[:, nxt].copy()
    y[:, ts + 1 >= W] = np.nan
    out["y_cnt"] = y.ravel()
    return pd.DataFrame(out)


def top_reasons(contribs, feature_names, k=3):
    contribs = np.asarray(contribs)
    order = np.argsort(-np.abs(contribs))[:k]
    return [{
        "feature": NICE.get(feature_names[i], feature_names[i]),
        "effect": "raises risk" if contribs[i] > 0 else "lowers risk",
        "strength": round(float(contribs[i]), 3),
    } for i in order]
