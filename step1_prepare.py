import glob
from pathlib import Path
import pandas as pd

DATA = Path("data")
OUT = Path("processed")
OUT.mkdir(exist_ok=True)

MODIS_COLS = ["latitude", "longitude", "brightness", "acq_date", "acq_time", "satellite", "confidence", "frp", "daynight", "type"]
VIIRS_COLS = ["latitude", "longitude", "bright_ti4", "acq_date", "acq_time", "satellite", "confidence", "frp", "daynight", "type"]


def load(folder, cols, sensor):
    files = sorted(glob.glob(str(DATA / folder / "*.csv")))
    print(f"{sensor}: {len(files)} files found")
    parts = []
    for f in files:
        d = pd.read_csv(f, usecols=cols, low_memory=False)
        d["country"] = "Pakistan" if "pakistan" in Path(f).name.lower() else "India"
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    df["year"] = df["acq_date"].dt.year
    df = df[df["type"] == 0]
    if sensor == "MODIS":
        df = df[df["confidence"] >= 30]
        df = df.rename(columns={"brightness": "bright"})
    else:
        df = df[df["confidence"].astype(str).str.lower().str[0] != "l"]
        df = df.rename(columns={"bright_ti4": "bright"})
    df = df.drop(columns=["type", "confidence"]).drop_duplicates()
    df["sensor"] = sensor
    return df


modis = load("modis", MODIS_COLS, "MODIS")
viirs = load("viirs", VIIRS_COLS, "VIIRS")

modis.to_parquet(OUT / "modis_clean.parquet", index=False)
viirs.to_parquet(OUT / "viirs_clean.parquet", index=False)

summary = pd.concat([
    modis.groupby(["year", "country"]).size().rename("MODIS"),
    viirs.groupby(["year", "country"]).size().rename("VIIRS"),
], axis=1).fillna(0).astype(int)

pd.set_option("display.max_rows", 100)
print(summary)
print("\nMODIS rows:", len(modis), "| VIIRS rows:", len(viirs))
