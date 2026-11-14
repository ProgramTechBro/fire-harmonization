from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IN = Path("processed")
OUT = Path("results/step2")
OUT.mkdir(parents=True, exist_ok=True)

PUNJAB = {"lat_min": 28.0, "lat_max": 34.0, "lon_min": 69.5, "lon_max": 77.5}

modis = pd.read_parquet(IN / "modis_clean.parquet")
viirs = pd.read_parquet(IN / "viirs_clean.parquet")

for df in (modis, viirs):
    df["month"] = df["acq_date"].dt.month


def in_punjab(df):
    return df[
        df["latitude"].between(PUNJAB["lat_min"], PUNJAB["lat_max"])
        & df["longitude"].between(PUNJAB["lon_min"], PUNJAB["lon_max"])
    ]


yearly = pd.concat([
    modis.groupby("year").size().rename("MODIS"),
    viirs.groupby("year").size().rename("VIIRS"),
], axis=1).fillna(0)

ax = yearly.plot(marker="o", figsize=(10, 5), title="Fire detections per year (Pakistan + India)")
ax.set_ylabel("Detections")
plt.tight_layout()
plt.savefig(OUT / "yearly_counts.png", dpi=120)
plt.close()

ratio = (yearly["VIIRS"] / yearly["MODIS"]).loc[2012:2025]
ax = ratio.plot(marker="o", figsize=(10, 5), title="VIIRS / MODIS ratio per year")
ax.set_ylabel("Ratio")
plt.tight_layout()
plt.savefig(OUT / "ratio_by_year.png", dpi=120)
plt.close()

mp = in_punjab(modis[modis["year"] >= 2012])
vp = in_punjab(viirs)
n_years = vp["year"].nunique()
monthly = pd.concat([
    (mp.groupby("month").size() / n_years).rename("MODIS"),
    (vp.groupby("month").size() / n_years).rename("VIIRS"),
], axis=1).fillna(0)

ax = monthly.plot(kind="bar", figsize=(10, 5), title="Punjab region: average fires per month (2012-2025)")
ax.set_ylabel("Average detections")
plt.tight_layout()
plt.savefig(OUT / "punjab_monthly.png", dpi=120)
plt.close()

sat = modis.groupby(["year", "satellite"]).size().unstack(fill_value=0)
ax = sat.plot(marker="o", figsize=(10, 5), title="MODIS detections by satellite")
ax.set_ylabel("Detections")
plt.tight_layout()
plt.savefig(OUT / "modis_by_satellite.png", dpi=120)
plt.close()

print("VIIRS/MODIS ratio per year:")
print(ratio.round(2))
print("\nPunjab average fires per month:")
print(monthly.round(0).astype(int))
print("\nMODIS satellites:", modis["satellite"].unique().tolist())
print("VIIRS satellites:", viirs["satellite"].unique().tolist())
print(f"\nCharts saved in {OUT}")
