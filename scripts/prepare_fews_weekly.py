"""Prepare historic FEWS NET Nigerian weekly crop price observations.

Place train/test Parquet splits in data/raw/fews_weekly/, then run:
    python -m pip install pyarrow
    python scripts/prepare_fews_weekly.py

Historical weekly observations are kept separate from World Bank estimates.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/fews_weekly"
OUT = ROOT / "data/processed"
SPLITS = ["train-00000-of-00001.parquet", "test-00000-of-00001.parquet"]
CROPS = {
    "Maize Grain (White)": "Maize", "Maize Grain (Yellow)": "Maize",
    "Rice (Milled)": "Rice", "Rice (5% Broken)": "Rice",
    "Cowpeas (White)": "Beans", "Cowpeas (Brown)": "Beans",
}
KG = {"kg": 1.0, "50_kg": 50.0, "100_kg": 100.0}
REQUIRED = {"country", "market", "admin_1", "longitude", "latitude", "product",
            "period_date", "price_type", "product_source", "unit", "currency", "value"}
SOURCE = "FEWS NET weekly prices via HDX / Electric Sheep Africa mirror"
SOURCE_URL = "https://huggingface.co/datasets/electricsheepafrica/africa-fewsnet-staple-food-price-data-for-nigeria-weekly-6837"

def clean_weekly_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected fields: {sorted(missing)}")
    sub = df.loc[df["country"].eq("Nigeria") & df["product"].isin(CROPS)].copy()
    sub["date"] = pd.to_datetime(sub["period_date"], errors="coerce", utc=True).dt.tz_localize(None)
    sub["unit_kg"] = sub["unit"].map(KG)
    sub["source_price_ngn"] = pd.to_numeric(sub["value"], errors="coerce")
    sub["latitude"] = pd.to_numeric(sub["latitude"], errors="coerce")
    sub["longitude"] = pd.to_numeric(sub["longitude"], errors="coerce")
    good = (sub["date"].notna() & sub["unit_kg"].notna()
            & sub["source_price_ngn"].gt(0)
            & sub["currency"].eq("NGN")
            & sub["latitude"].between(3, 15)
            & sub["longitude"].between(2, 16)
            & sub["market"].notna() & sub["admin_1"].notna()
            & sub["price_type"].isin(["Retail", "Wholesale"]))
    clean = sub.loc[good].copy()
    clean["crop"] = clean["product"].map(CROPS)
    clean["price_ngn_per_kg"] = clean["source_price_ngn"] / clean["unit_kg"]
    clean["price_kind"] = "reported_historical"
    clean["source"] = SOURCE
    clean["source_url"] = SOURCE_URL
    clean = clean.rename(columns={"product":"variety", "admin_1":"state",
                                  "product_source":"product_origin"})
    columns = ["date", "crop", "variety", "state", "market",
               "latitude", "longitude", "price_type", "product_origin",
               "unit", "unit_kg", "source_price_ngn", "price_ngn_per_kg",
               "currency", "price_kind", "source", "source_url"]
    clean = clean[columns].drop_duplicates()
    key = ["date", "variety", "state", "market", "price_type", "product_origin", "unit"]
    if clean.duplicated(key).any():
        raise ValueError("Conflicting duplicate weekly prices: resolve before model use.")
    clean = clean.sort_values(["crop","variety","state","market","price_type","date"]).reset_index(drop=True)
    profile = {"raw_rows": int(len(df)), "target_crop_rows": int(len(sub)),
               "excluded_target_rows": int((~good).sum()), "clean_rows": int(len(clean)),
               "markets": int(clean[["state","market"]].drop_duplicates().shape[0]),
               "states": int(clean.state.nunique()),
               "from_date": str(clean.date.min().date()) if len(clean) else None,
               "through_date": str(clean.date.max().date()) if len(clean) else None,
               "by_crop": {str(k):int(v) for k,v in clean.crop.value_counts().items()},
               "source": SOURCE, "source_url": SOURCE_URL,
               "warning": "HISTORICAL through May 2024; not live quotes or FCT price coverage."}
    return clean, profile

def main():
    paths = [RAW / name for name in SPLITS]
    if not all(p.is_file() for p in paths):
        raise SystemExit("Place both train/test Parquet files in data/raw/fews_weekly/")
    # Original Hugging Face splits are randomized, NOT chronological.
    df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    clean, profile = clean_weekly_prices(df)
    OUT.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUT / "fews_weekly_prices.csv", index=False,
                 float_format="%.5f", date_format="%Y-%m-%d")
    (OUT / "fews_weekly_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(json.dumps(profile, indent=2))
    print("Wrote", OUT / "fews_weekly_prices.csv")

if __name__ == "__main__":
    main()
