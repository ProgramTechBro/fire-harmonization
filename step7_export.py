import json
import shutil
import time
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import features as fx

IN = Path("processed")
MOD = Path("models")
RES = Path("results")
OUT = Path("web_data")
OUT_MOD = OUT / "models"
OUT_MOD.mkdir(parents=True, exist_ok=True)
FEATURE_START_YEAR = 2022

hw = pd.read_parquet(IN / "harmonized_weekly.parquet")

cells = hw.groupby("cell_id", sort=True).agg(
    lat=("lat", "first"), lon=("lon", "first"), country=("country", "first"), punjab=("punjab", "first")
).reset_index()
cells["country"] = cells["country"].astype(str)
cells["cell_id"] = cells["cell_id"].astype("int16")
cells.to_parquet(OUT / "cells.parquet", index=False)

cal = hw[["cell_id", "week", "m_count", "v_count", "h_count", "is_estimated"]].copy()
cal = cal[(cal["h_count"] >= 0.1) | (cal["m_count"] > 0) | (cal["v_count"].fillna(0) > 0)]
cal["cell_id"] = cal["cell_id"].astype("int16")
cal["m_count"] = cal["m_count"].astype("int16")
cal["h_count"] = cal["h_count"].round(2).astype("float32")
cal["is_estimated"] = cal["is_estimated"].astype("int8")
cal.to_parquet(OUT / "calendar_weekly.parquet", index=False)
print(f"Calendar rows: {len(cal):,}")

inp = fx.forecast_inputs(hw[["cell_id", "lat", "lon", "country", "punjab", "week", "h_count", "v_count"]])
del hw, cal
weeks = inp["weeks"]
W = len(weeks)
ts = np.array([t for t in range(fx.HISTORY, W)
               if (weeks[t] + pd.Timedelta(days=7)).year >= FEATURE_START_YEAR])
rows = fx.build_rows(inp, ts)
del inp

cfg = json.load(open(MOD / "forecast_config.json"))
FEATS = cfg["features"]
feat = rows[["cell_id", "target_week"] + FEATS + ["y_cnt"]].copy()
del rows
for c in FEATS:
    if feat[c].dtype == "float64":
        feat[c] = feat[c].astype("float32")
feat["cell_id"] = feat["cell_id"].astype("int16")
feat.to_parquet(OUT / "forecast_features.parquet", index=False)
print(f"Forecast feature rows: {len(feat):,} "
      f"({pd.Timestamp(feat['target_week'].min()).date()} to {pd.Timestamp(feat['target_week'].max()).date()})")

for name in ["forecast_fire_prob.txt", "forecast_fire_count.txt", "forecast_config.json"]:
    shutil.copy(MOD / name, OUT_MOD / name)

clf = lgb.Booster(model_file=str(MOD / "forecast_fire_prob.txt"))
reg = lgb.Booster(model_file=str(MOD / "forecast_fire_count.txt"))

fc = pd.read_parquet(IN / "forecasts.parquet", columns=["cell_id", "target_week", "p_fire"])
fc["cell_id"] = fc["cell_id"].astype("int16")
sample = feat.sample(min(20000, len(feat)), random_state=1)
check = sample[["cell_id", "target_week"]].assign(p_new=clf.predict(sample[FEATS]))
check = check.merge(fc, on=["cell_id", "target_week"], how="inner")
max_diff = float((check["p_new"] - check["p_fire"]).abs().max())
print(f"Consistency check on {len(check):,} rows, max difference: {max_diff:.2e} ->",
      "PASS" if max_diff < 1e-4 else "FAIL")

latest = feat["target_week"].max()
X = feat.loc[feat["target_week"] == latest, FEATS]
t0 = time.time()
clf.predict(X)
reg.predict(X)
t1 = time.time()
explainer = shap.TreeExplainer(clf)
t2 = time.time()
explainer.shap_values(X.iloc[[0]])
t3 = time.time()
print(f"Live map prediction ({len(X):,} boxes): {t1 - t0:.2f}s | SHAP setup: {t2 - t1:.2f}s | "
      f"one-box explanation: {t3 - t2:.3f}s")


def csv_records(path):
    return pd.read_csv(path, index_col=0).round(4).reset_index().rename(columns={"index": "method"}).to_dict("records")


metrics = {
    "harmonization_test_2024_2025": csv_records(RES / "step4" / "metrics_test_2024_2025.csv"),
    "forecast_classification_test_2024_2025": csv_records(RES / "step5" / "classification_test_2024_2025.csv"),
    "forecast_count_test_2024_2025": csv_records(RES / "step5" / "count_test_2024_2025.csv"),
    "yearly_totals": pd.read_csv(RES / "step4" / "yearly_totals.csv").to_dict("records"),
    "latest_forecast_week": str(pd.Timestamp(latest).date()),
    "feature_start_year": FEATURE_START_YEAR,
}
with open(OUT / "metrics.json", "w") as f:
    json.dump(metrics, f, indent=2, default=str)

print("\nFiles in web_data:")
for p in sorted(OUT.rglob("*")):
    if p.is_file():
        print(f"  {p.relative_to(OUT)}  {p.stat().st_size / 1e6:.1f} MB")
