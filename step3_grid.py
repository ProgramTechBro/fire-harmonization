from pathlib import Path
import numpy as np
import pandas as pd

IN = Path("processed")
RES = 0.25
MIN_DETECTIONS = 5
AQUA_START = pd.Timestamp("2002-07-01")
VIIRS_START = pd.Timestamp("2012-01-16")

modis = pd.read_parquet(IN / "modis_clean.parquet")
viirs = pd.read_parquet(IN / "viirs_clean.parquet")


def add_keys(df):
    df["lat_i"] = np.floor(df["latitude"] / RES).astype("int32")
    df["lon_i"] = np.floor(df["longitude"] / RES).astype("int32")
    df["week"] = (df["acq_date"] - pd.to_timedelta(df["acq_date"].dt.dayofweek, unit="D")).dt.normalize()
    return df


modis = add_keys(modis)
viirs = add_keys(viirs)
keys = ["lat_i", "lon_i", "week"]

modis["is_terra"] = (modis["satellite"] == "Terra").astype("int32")
modis["is_day"] = (modis["daynight"] == "D").astype("int32")

m = modis.groupby(keys).agg(
    m_count=("frp", "size"),
    m_frp_sum=("frp", "sum"),
    m_frp_max=("frp", "max"),
    m_bright_mean=("bright", "mean"),
    m_terra=("is_terra", "sum"),
    m_day=("is_day", "sum"),
).reset_index()

v = viirs.groupby(keys).agg(
    v_count=("frp", "size"),
    v_frp_sum=("frp", "sum"),
).reset_index()

both = pd.concat([modis[["lat_i", "lon_i", "country"]], viirs[["lat_i", "lon_i", "country"]]])
by_country = both.groupby(["lat_i", "lon_i", "country"]).size().rename("n").reset_index()
totals = by_country.groupby(["lat_i", "lon_i"])["n"].sum().rename("total")
main_country = by_country.loc[by_country.groupby(["lat_i", "lon_i"])["n"].idxmax(), ["lat_i", "lon_i", "country"]]
cells = main_country.merge(totals, on=["lat_i", "lon_i"])
cells = cells[cells["total"] >= MIN_DETECTIONS].reset_index(drop=True)
cells["cell_id"] = np.arange(len(cells), dtype="int32")
cells["lat"] = (cells["lat_i"] * RES + RES / 2).astype("float32")
cells["lon"] = (cells["lon_i"] * RES + RES / 2).astype("float32")

weeks = pd.date_range(modis["week"].min(), max(modis["week"].max(), viirs["week"].max()), freq="W-MON")
panel = cells[["cell_id", "lat_i", "lon_i", "lat", "lon", "country"]].merge(pd.DataFrame({"week": weeks}), how="cross")
panel = panel.merge(m, on=keys, how="left").merge(v, on=keys, how="left")

m_cols = ["m_count", "m_frp_sum", "m_frp_max", "m_bright_mean", "m_terra", "m_day"]
panel[m_cols] = panel[m_cols].fillna(0)
panel[["v_count", "v_frp_sum"]] = panel[["v_count", "v_frp_sum"]].fillna(0)
panel.loc[panel["week"] < VIIRS_START, ["v_count", "v_frp_sum"]] = np.nan

panel["year"] = panel["week"].dt.year.astype("int16")
panel["month"] = panel["week"].dt.month.astype("int8")
panel["woy"] = panel["week"].dt.isocalendar().week.astype("int8")
panel["aqua_on"] = (panel["week"] >= AQUA_START).astype("int8")
panel["viirs_on"] = (panel["week"] >= VIIRS_START).astype("int8")
panel["country"] = panel["country"].astype("category")

for c in m_cols + ["v_count", "v_frp_sum"]:
    panel[c] = panel[c].astype("float32")

panel = panel.drop(columns=["lat_i", "lon_i"]).sort_values(["cell_id", "week"]).reset_index(drop=True)

panel.to_parquet(IN / "grid_weekly.parquet", index=False)
cells.drop(columns=["lat_i", "lon_i"]).to_parquet(IN / "cells.parquet", index=False)

print("Cells:", len(cells), "| Pakistan:", (cells["country"] == "Pakistan").sum(), "| India:", (cells["country"] == "India").sum())
print("Weeks:", len(weeks), f"({weeks.min().date()} to {weeks.max().date()})")
print("Panel rows:", len(panel))
print("Memory (MB):", round(panel.memory_usage(deep=True).sum() / 1e6, 1))
print("MODIS detections kept:", int(panel["m_count"].sum()), "of", len(modis))
print("VIIRS detections kept:", int(panel["v_count"].sum()), "of", len(viirs))
print("Cell-weeks with any MODIS fire:", int((panel["m_count"] > 0).sum()))
print("Cell-weeks with any VIIRS fire:", int((panel["v_count"] > 0).sum()))
print(panel.head())
