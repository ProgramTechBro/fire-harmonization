import json
import shutil
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from . import config, geo


def build_bundle(data_dir, out_dir):
    import lightgbm as lgb

    t0 = time.time()
    data_dir, out = Path(data_dir), Path(out_dir)
    tmp = out.with_name(out.name + "_building")
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "calendars").mkdir(parents=True)
    print(f"Building bundle from {data_dir}")

    cfg = json.loads((data_dir / "models" / "forecast_config.json").read_text())
    features = cfg["features"]
    metrics_path = data_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}

    cells = pd.read_parquet(data_dir / "cells.parquet").sort_values("cell_id")
    cells = cells[["cell_id", "lat", "lon", "country", "punjab"]]
    (tmp / "cells.json").write_text(json.dumps({
        "cell_id": cells["cell_id"].astype(int).tolist(),
        "lat": cells["lat"].astype(float).round(4).tolist(),
        "lon": cells["lon"].astype(float).round(4).tolist(),
        "country": cells["country"].astype(str).tolist(),
        "punjab": cells["punjab"].astype(int).tolist(),
    }))

    feat = pd.read_parquet(data_dir / "forecast_features.parquet", columns=["cell_id", "target_week", "y_cnt"] + features)
    feat["target_week"] = pd.to_datetime(feat["target_week"])
    feat = feat.sort_values(["target_week", "cell_id"]).reset_index(drop=True)
    fweeks = pd.DatetimeIndex(np.unique(feat["target_week"].to_numpy()))
    X = feat[features].to_numpy(dtype="float32")
    clf = lgb.Booster(model_file=str(data_dir / "models" / "forecast_fire_prob.txt"))
    reg = lgb.Booster(model_file=str(data_dir / "models" / "forecast_fire_count.txt"))
    np.save(tmp / "fp.npy", clf.predict(feat[features]).astype("float32"))
    np.save(tmp / "fc.npy", reg.predict(feat[features]).astype("float32"))
    del clf, reg
    np.save(tmp / "fx.npy", X)
    np.save(tmp / "fcell.npy", feat["cell_id"].to_numpy(dtype="int16"))
    np.save(tmp / "fwk.npy", fweeks.get_indexer(feat["target_week"]).astype("int16"))
    np.save(tmp / "fy.npy", feat["y_cnt"].to_numpy(dtype="float32"))
    print(f"Forecasts: {len(feat):,} rows, {len(fweeks)} weeks")
    del feat, X

    cal = pd.read_parquet(data_dir / "calendar_weekly.parquet", columns=["cell_id", "week", "m_count", "v_count", "h_count"])
    cal["week"] = pd.to_datetime(cal["week"])
    first = cal["week"].min()
    nweeks = len(pd.date_range(first, cal["week"].max(), freq="W-MON"))
    cal["wk"] = ((cal["week"] - first).dt.days // 7).astype("int16")
    cal = cal.sort_values(["cell_id", "wk"]).reset_index(drop=True)
    np.save(tmp / "ccell.npy", cal["cell_id"].to_numpy(dtype="int16"))
    np.save(tmp / "cwk.npy", cal["wk"].to_numpy(dtype="int16"))
    np.save(tmp / "ch.npy", cal["h_count"].to_numpy(dtype="float32"))
    np.save(tmp / "cm.npy", cal["m_count"].to_numpy(dtype="int16"))
    np.save(tmp / "cv.npy", cal["v_count"].to_numpy(dtype="float32"))
    print(f"Calendar: {len(cal):,} rows, {nweeks} weeks")
    del cal

    shutil.copy(data_dir / "models" / "forecast_fire_prob.txt", tmp / "forecast_fire_prob.txt")
    (tmp / "meta.json").write_text(json.dumps({
        "features": features,
        "threshold": cfg["threshold"],
        "forecast_weeks": [str(w.date()) for w in fweeks],
        "calendar_first": str(first.date()),
        "calendar_weeks": nweeks,
        "metrics": metrics,
    }))

    from .store import Store

    store = Store(data_dir, tmp)
    for region in geo.REGIONS:
        ids, label = store.region_cells(region)
        payload = store.calendar_payload(("__build__", region), ids, label)
        (tmp / "calendars" / f"{region}.json").write_text(json.dumps(payload))
    print(f"Region calendars: {len(geo.REGIONS)}")
    del store

    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6
    print(f"Bundle ready at {out} ({size:.0f} MB) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    build_bundle(sys.argv[1] if len(sys.argv) > 1 else config.DATA_DIR,
                 sys.argv[2] if len(sys.argv) > 2 else config.PRECOMPUTED_DIR)
