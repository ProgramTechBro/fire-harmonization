import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import features as fx

warnings.filterwarnings("ignore")

IN = Path("processed")
MOD = Path("models")
RES = Path("results/step6")
RES.mkdir(parents=True, exist_ok=True)
N = 5000
EXAMPLE_WEEK = pd.Timestamp("2025-11-03")


def explain(explainer, X):
    ex = explainer(X)
    values = ex.values[:, :, 1] if ex.values.ndim == 3 else ex.values
    base = ex.base_values[:, 1] if np.ndim(ex.base_values) == 2 else ex.base_values
    return shap.Explanation(values=values, base_values=base, data=X.to_numpy(),
                            feature_names=[fx.NICE.get(c, c) for c in X.columns])


def save_plots(explainer, X, name, title):
    print(f"Explaining {name} on {len(X):,} rows")
    ex = explain(explainer, X)
    shap.plots.beeswarm(ex, max_display=12, show=False)
    plt.title(title)
    plt.savefig(RES / f"{name}_beeswarm.png", dpi=120, bbox_inches="tight")
    plt.close()
    shap.plots.bar(ex, max_display=12, show=False)
    plt.title(title)
    plt.savefig(RES / f"{name}_bar.png", dpi=120, bbox_inches="tight")
    plt.close()
    imp = pd.Series(np.abs(ex.values).mean(0), index=ex.feature_names).sort_values(ascending=False)
    imp.round(4).to_csv(RES / f"{name}_importance.csv", header=["mean_abs_shap"])
    print(imp.head(6).round(3).to_string(), "\n")


grid = fx.add_harmonize_features(pd.read_parquet(IN / "grid_weekly.parquet"))
ta = grid[(grid["year"] >= 2024) & ((grid["m_count"] + grid["v_count"]) > 0)]
XA = ta[fx.F_FULL].sample(min(N, len(ta)), random_state=42)
full = lgb.Booster(model_file=str(MOD / "harmonize_full.txt"))
save_plots(shap.TreeExplainer(full), XA, "modelA", "Model A: what drives the VIIRS-equivalent estimate")
del grid, ta, XA

hw = pd.read_parquet(IN / "harmonized_weekly.parquet",
                     columns=["cell_id", "lat", "lon", "country", "punjab", "week", "h_count", "v_count"])
inp = fx.forecast_inputs(hw)
del hw
weeks = inp["weeks"]
ts = np.array([t for t in range(fx.HISTORY, len(weeks) - 1) if (weeks[t] + pd.Timedelta(days=7)).year >= 2024])
rows = fx.build_rows(inp, ts)

cfg = json.load(open(MOD / "forecast_config.json"))
FEATS = cfg["features"]
clf = lgb.Booster(model_file=str(MOD / "forecast_fire_prob.txt"))
explB = shap.TreeExplainer(clf)

save_plots(explB, rows[FEATS].sample(N, random_state=42), "modelB_all",
           "Model B: what drives next-week fire risk")

months = pd.DatetimeIndex(rows["target_week"]).month
pj = rows[(rows["punjab"] == 1) & months.isin([10, 11])]
save_plots(explB, pj[FEATS].sample(min(N, len(pj)), random_state=42), "modelB_punjab_octnov",
           "Model B in Punjab burning season (Oct-Nov)")

cand = rows[(rows["punjab"] == 1) & (rows["target_week"] == EXAMPLE_WEEK)].copy()
cand["p_fire"] = clf.predict(cand[FEATS])
one = cand.sort_values("p_fire", ascending=False).head(1)
ex1 = explain(explB, one[FEATS])
shap.plots.waterfall(ex1[0], max_display=10, show=False)
plt.savefig(RES / "example_punjab_box_waterfall.png", dpi=120, bbox_inches="tight")
plt.close()

row = one.iloc[0]
reasons = fx.top_reasons(ex1.values[0], FEATS)
example = {
    "target_week": str(EXAMPLE_WEEK.date()),
    "lat": float(row["lat"]),
    "lon": float(row["lon"]),
    "fire_probability": round(float(row["p_fire"]), 3),
    "actual_viirs_fires": float(row["y_cnt"]),
    "top_reasons": reasons,
}
with open(RES / "example_explanation.json", "w") as f:
    json.dump(example, f, indent=2)

print("Example: highest-risk Punjab box for week of", EXAMPLE_WEEK.date())
print(json.dumps(example, indent=2))
print(f"\nCharts saved in {RES}")
