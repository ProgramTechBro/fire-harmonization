from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IN = Path("processed")
MOD = Path("models")
RES = Path("results/step4")
MOD.mkdir(exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

PUNJAB = {"lat_min": 28.0, "lat_max": 34.0, "lon_min": 69.5, "lon_max": 77.5}

df = pd.read_parquet(IN / "grid_weekly.parquet").sort_values(["cell_id", "week"]).reset_index(drop=True)

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
df["punjab"] = (
    df["lat"].between(PUNJAB["lat_min"], PUNJAB["lat_max"])
    & df["lon"].between(PUNJAB["lon_min"], PUNJAB["lon_max"])
).astype("int8")

F_FULL = ["m_count", "m_aqua", "m_terra", "m_frp_sum", "m_frp_max", "m_bright_mean", "m_day",
          "m_prev", "m_next", "cell_m_mean", "cell_t_mean", "cell_woy_t_mean", "lat", "lon", "woy", "month"]
F_TERRA = ["m_terra", "t_prev", "t_next", "cell_t_mean", "cell_woy_t_mean", "lat", "lon", "woy", "month"]

train = df[(df["viirs_on"] == 1) & (df["year"] <= 2021)]
valid = df[df["year"].between(2022, 2023)]
test = df[df["year"] >= 2024].copy()

PARAMS = {
    "objective": "poisson",
    "learning_rate": 0.05,
    "num_leaves": 127,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "verbose": -1,
}


def fit(features, name):
    print(f"\nTraining {name} on {len(train):,} rows")
    dtr = lgb.Dataset(train[features], train["v_count"])
    dva = lgb.Dataset(valid[features], valid["v_count"], reference=dtr)
    model = lgb.train(PARAMS, dtr, 3000, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)])
    model.save_model(str(MOD / f"{name}.txt"), num_iteration=model.best_iteration)
    return model


def scores(y, p, frame):
    weekly = pd.DataFrame({"week": frame["week"], "y": y, "p": p}).groupby("week")[["y", "p"]].sum()
    pj = frame["punjab"] == 1
    pweekly = pd.DataFrame({"week": frame.loc[pj, "week"], "y": y[pj], "p": p[pj]}).groupby("week")[["y", "p"]].sum()
    return {
        "cell_MAE": mean_absolute_error(y, p),
        "cell_RMSE": mean_squared_error(y, p) ** 0.5,
        "cell_R2": r2_score(y, p),
        "weekly_total_R2": r2_score(weekly["y"], weekly["p"]),
        "punjab_weekly_R2": r2_score(pweekly["y"], pweekly["p"]),
    }


full = fit(F_FULL, "harmonize_full")
terra = fit(F_TERRA, "harmonize_terra")

k_full = train["v_count"].sum() / train["m_count"].sum()
k_terra = train["v_count"].sum() / train["m_terra"].sum()

y = test["v_count"].values
test["p_full"] = full.predict(test[F_FULL], num_iteration=full.best_iteration)
test["p_terra"] = terra.predict(test[F_TERRA], num_iteration=terra.best_iteration)

metrics = pd.DataFrame({
    "Baseline ratio (MODIS x k)": scores(y, test["m_count"].values * k_full, test),
    "Model A full (Terra+Aqua)": scores(y, test["p_full"].values, test),
    "Baseline ratio (Terra x k)": scores(y, test["m_terra"].values * k_terra, test),
    "Model A Terra-only": scores(y, test["p_terra"].values, test),
}).T.round(4)
metrics.to_csv(RES / "metrics_test_2024_2025.csv")
print("\nTest results (2024-2025):")
print(metrics.to_string())

aqua = df["aqua_on"] == 1
df["v_model"] = np.nan
df.loc[aqua, "v_model"] = full.predict(df.loc[aqua, F_FULL], num_iteration=full.best_iteration)
df.loc[~aqua, "v_model"] = terra.predict(df.loc[~aqua, F_TERRA], num_iteration=terra.best_iteration)
df["h_count"] = np.where(df["viirs_on"] == 1, df["v_count"], df["v_model"]).astype("float32")
df["is_estimated"] = (df["viirs_on"] == 0).astype("int8")

out_cols = ["cell_id", "lat", "lon", "country", "punjab", "week", "year", "month", "woy",
            "m_count", "m_frp_sum", "v_count", "v_model", "h_count", "is_estimated"]
df[out_cols].to_parquet(IN / "harmonized_weekly.parquet", index=False)

yearly = df.groupby("year").agg(
    MODIS_raw=("m_count", "sum"),
    VIIRS_actual=("v_count", "sum"),
    Model_estimate=("v_model", "sum"),
    Harmonized=("h_count", "sum"),
)
yearly.loc[yearly.index < 2012, "VIIRS_actual"] = np.nan
yearly = yearly.loc[2001:]
yearly.round(0).to_csv(RES / "yearly_totals.csv")

ax = yearly[["MODIS_raw", "VIIRS_actual", "Model_estimate"]].plot(marker="o", figsize=(11, 5),
                                                                  title="Harmonized fire record (Pakistan + India)")
ax.axvline(2012, color="gray", linestyle="--")
ax.set_ylabel("Detections (VIIRS-equivalent)")
plt.tight_layout()
plt.savefig(RES / "harmonized_yearly.png", dpi=120)
plt.close()

pt = test[test["punjab"] == 1].groupby("week").agg(
    VIIRS_actual=("v_count", "sum"),
    Model_A=("p_full", "sum"),
    Baseline=("m_count", lambda s: s.sum() * k_full),
)
ax = pt.plot(figsize=(12, 5), title="Punjab weekly fires, test period 2024-2025")
ax.set_ylabel("Detections")
plt.tight_layout()
plt.savefig(RES / "punjab_test_weekly.png", dpi=120)
plt.close()

imp = pd.Series(full.feature_importance("gain"), index=F_FULL).sort_values()
ax = imp.plot(kind="barh", figsize=(8, 6), title="Model A feature importance (gain)")
plt.tight_layout()
plt.savefig(RES / "feature_importance.png", dpi=120)
plt.close()

print("\nYearly totals:")
print(yearly.round(0).to_string())
print(f"\nSaved models in {MOD}, results in {RES}, data in {IN / 'harmonized_weekly.parquet'}")
