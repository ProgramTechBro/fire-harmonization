import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy import sparse
from sklearn.metrics import (roc_auc_score, average_precision_score, precision_recall_curve,
                             precision_recall_fscore_support, mean_absolute_error, r2_score)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=RuntimeWarning)

IN = Path("processed")
MOD = Path("models")
RES = Path("results/step5")
MOD.mkdir(exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

GRID = 0.25
HISTORY = 259

df = pd.read_parquet(IN / "harmonized_weekly.parquet",
                     columns=["cell_id", "lat", "lon", "country", "punjab", "week", "h_count", "v_count"])
df = df.sort_values(["cell_id", "week"]).reset_index(drop=True)
cells = df.groupby("cell_id", sort=True).agg(
    lat=("lat", "first"), lon=("lon", "first"), punjab=("punjab", "first"), country=("country", "first")
).reset_index()
weeks = pd.DatetimeIndex(np.sort(df["week"].unique()))
C, W = len(cells), len(weeks)
H = df["h_count"].to_numpy(dtype="float32").reshape(C, W)
V = df["v_count"].to_numpy(dtype="float32").reshape(C, W)
del df

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
A = sparse.csr_matrix((np.ones(len(r), dtype="float32"), (r, c)), shape=(C, C))
NB = np.asarray(A @ H, dtype="float32")


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
    return np.nanmean(np.stack(arrs), axis=0).astype("float32")


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
FEATS = list(F) + ["lat", "lon", "woy", "month"]


def build(ts):
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


data = build(np.arange(HISTORY, W - 1))
data = data[data["y_cnt"].notna()].reset_index(drop=True)
data["y_bin"] = (data["y_cnt"] >= 1).astype("int8")
data["year"] = pd.DatetimeIndex(data["target_week"]).year

train = data[data["year"] <= 2021]
valid = data[data["year"].between(2022, 2023)]
test = data[data["year"] >= 2024].copy()
print(f"Rows  train: {len(train):,}  valid: {len(valid):,}  test: {len(test):,}")
print(f"Fire-week rate in train: {train['y_bin'].mean():.3f}")

BASE = {"learning_rate": 0.05, "num_leaves": 127, "min_data_in_leaf": 200, "feature_fraction": 0.9,
        "bagging_fraction": 0.8, "bagging_freq": 1, "verbose": -1}


def fit(params, target, name):
    print(f"\nTraining {name}")
    dtr = lgb.Dataset(train[FEATS], train[target])
    dva = lgb.Dataset(valid[FEATS], valid[target], reference=dtr)
    model = lgb.train(params, dtr, 3000, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)])
    model.save_model(str(MOD / f"{name}.txt"), num_iteration=model.best_iteration)
    return model


clf = fit({**BASE, "objective": "binary", "metric": "auc"}, "y_bin", "forecast_fire_prob")
reg = fit({**BASE, "objective": "poisson"}, "y_cnt", "forecast_fire_count")

p_valid = clf.predict(valid[FEATS], num_iteration=clf.best_iteration)
prec, rec, thr = precision_recall_curve(valid["y_bin"], p_valid)
f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
best = int(np.nanargmax(f1[:-1]))
threshold = float(thr[best])

test["p_fire"] = clf.predict(test[FEATS], num_iteration=clf.best_iteration)
test["exp_count"] = reg.predict(test[FEATS], num_iteration=reg.best_iteration)


def cls_scores(y, score, pred):
    p, r_, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    return {"ROC_AUC": roc_auc_score(y, score), "PR_AUC": average_precision_score(y, score),
            "Precision": p, "Recall": r_, "F1": f}


y = test["y_bin"].to_numpy()
pj = test["punjab"].to_numpy() == 1
cls = pd.DataFrame({
    "Persistence (fire this week)": cls_scores(y, test["h_now"], test["h_now"] >= 1),
    "Climatology (5-yr same week)": cls_scores(y, test["h_clim5"].fillna(0), test["h_clim5"].fillna(0) >= 1),
    "Model B": cls_scores(y, test["p_fire"], test["p_fire"] >= threshold),
    "Model B (Punjab only)": cls_scores(y[pj], test.loc[pj, "p_fire"], test.loc[pj, "p_fire"] >= threshold),
}).T.round(4)


def cnt_scores(frame, col):
    wk = frame.groupby("target_week")[["y_cnt", col]].sum()
    pf = frame[frame["punjab"] == 1].groupby("target_week")[["y_cnt", col]].sum()
    return {"cell_MAE": mean_absolute_error(frame["y_cnt"], frame[col]),
            "cell_R2": r2_score(frame["y_cnt"], frame[col]),
            "weekly_total_R2": r2_score(wk["y_cnt"], wk[col]),
            "punjab_weekly_R2": r2_score(pf["y_cnt"], pf[col])}


test["h_clim5_f"] = test["h_clim5"].fillna(0)
cnt = pd.DataFrame({
    "Persistence": cnt_scores(test, "h_now"),
    "Climatology": cnt_scores(test, "h_clim5_f"),
    "Model B count": cnt_scores(test, "exp_count"),
}).T.round(4)

cls.to_csv(RES / "classification_test_2024_2025.csv")
cnt.to_csv(RES / "count_test_2024_2025.csv")
print(f"\nDecision threshold (best F1 on 2022-2023): {threshold:.3f}")
print("\nWill there be fire next week? (test 2024-2025)")
print(cls.to_string())
print("\nHow many fires next week? (test 2024-2025)")
print(cnt.to_string())

pw = test[test["punjab"] == 1].groupby("target_week").agg(
    VIIRS_actual=("y_cnt", "sum"), Model_B=("exp_count", "sum"), Persistence=("h_now", "sum"))
ax = pw.plot(figsize=(12, 5), title="Punjab: next-week fire forecast vs actual (2024-2025)")
ax.set_ylabel("Detections")
plt.tight_layout()
plt.savefig(RES / "punjab_forecast_test.png", dpi=120)
plt.close()

imp = pd.Series(clf.feature_importance("gain"), index=FEATS).sort_values()
ax = imp.plot(kind="barh", figsize=(8, 6), title="Model B feature importance (gain)")
plt.tight_layout()
plt.savefig(RES / "feature_importance.png", dpi=120)
plt.close()

latest = build(np.array([W - 1]))
everything = pd.concat([data.drop(columns=["y_bin", "year"]), latest], ignore_index=True)
everything["p_fire"] = clf.predict(everything[FEATS], num_iteration=clf.best_iteration).astype("float32")
everything["exp_count"] = reg.predict(everything[FEATS], num_iteration=reg.best_iteration).astype("float32")
everything[["cell_id", "lat", "lon", "country", "punjab", "target_week", "p_fire", "exp_count", "y_cnt"]].to_parquet(
    IN / "forecasts.parquet", index=False)

with open(MOD / "forecast_config.json", "w") as f:
    json.dump({"features": FEATS, "threshold": threshold, "grid_deg": GRID, "history_weeks": HISTORY,
               "last_data_week": str(weeks[-1].date())}, f, indent=2)

print(f"\nForecast for week of {(weeks[-1] + pd.Timedelta(days=7)).date()} included in {IN / 'forecasts.parquet'}")
print(f"Models in {MOD}, charts and metrics in {RES}")
