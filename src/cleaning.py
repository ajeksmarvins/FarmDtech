"""World Bank Nigeria RTFP data normalization for FarmDtech.

The commodity columns are *observed survey prices*, while c_* columns
are modelled monthly closing-price estimates. Never confuse the two.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np

# Original basket unit sizes are encoded in the World Bank `components` field.
# Do not mix the two distinct rice series; the MVP uses 1 kg rice_fao.
CROPS = {
    "Beans": {"code": "beans", "kg_per_unit": 2.5, "label": "Beans (2.5 kg basket)"},
    "Maize": {"code": "maize_fao", "kg_per_unit": 1.0, "label": "Maize (FAO, 1 kg)"},
    "Rice": {"code": "rice_fao", "kg_per_unit": 1.0, "label": "Rice (FAO, 1 kg)"},
}
EXCLUDED_STATES = {"National Average", "Market Average", "Geopolitical Zone"}
REQUIRED = {"geo_id", "price_date", "adm1_name", "mkt_name", "lat", "lon", "currency"}
OUTPUT_COLUMNS = ["date", "crop", "crop_code", "market_id", "market", "state", "latitude", "longitude", "price_ngn_per_kg", "price_kind", "source", "original_unit_kg", "source_value_ngn", "data_coverage_recent", "survey_confidence"]


def clean_world_bank(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    """Transform wide World Bank data into normalized long-form market prices.

    Retains observed survey values and estimated series as separate records.
    Estimates are never relabeled as live observations.
    """
    df = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source, low_memory=False)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Required columns are missing: {sorted(missing)}")
    df = df.loc[(df["currency"] == "NGN") & ~df["adm1_name"].isin(EXCLUDED_STATES)].copy()
    df = df.dropna(subset=["geo_id", "mkt_name", "lat", "lon", "price_date"])
    df["price_date"] = pd.to_datetime(df["price_date"], errors="coerce")
    df = df.dropna(subset=["price_date"])
    df = df.drop_duplicates(subset=["geo_id", "price_date"], keep="last")
    parts = []
    for crop, settings in CROPS.items():
        code = settings["code"]
        unit = settings["kg_per_unit"]
        for price_kind, col in [("observed", code), ("estimated", f"c_{code}")]:
            if col not in df.columns:
                raise ValueError(f"Missing {col} commodity column")
            sub = df[["price_date", "geo_id", "mkt_name", "adm1_name", "lat", "lon", col]].copy()
            sub["source_value_ngn"] = pd.to_numeric(sub[col], errors="coerce")
            sub = sub.dropna(subset=["source_value_ngn"])
            sub = sub[sub["source_value_ngn"] > 0]
            sub["price_ngn_per_kg"] = sub["source_value_ngn"] / unit
            sub["crop"] = crop
            sub["crop_code"] = code
            sub["price_kind"] = price_kind
            sub["source"] = "World Bank RTFP (observed survey)" if price_kind == "observed" else "World Bank RTFP (modelled estimate)"
            sub["original_unit_kg"] = unit
            sub["data_coverage_recent"] = pd.to_numeric(df.loc[sub.index, "data_coverage_recent"], errors="coerce") if "data_coverage_recent" in df else np.nan
            sub["survey_confidence"] = pd.to_numeric(df.loc[sub.index, "index_confidence_score"], errors="coerce") if "index_confidence_score" in df else np.nan
            sub = sub.rename(columns={"price_date": "date", "geo_id": "market_id", "mkt_name": "market", "adm1_name": "state", "lat": "latitude", "lon": "longitude"})
            parts.append(sub[OUTPUT_COLUMNS])
    if not parts:
        raise ValueError("No price records after cleaning")
    cleaned = pd.concat(parts, ignore_index=True)
    cleaned = cleaned.drop_duplicates(subset=["date", "market_id", "crop", "price_kind"], keep="last")
    cleaned = cleaned.sort_values(["crop", "market", "date", "price_kind"]).reset_index(drop=True)
    cleaned["date"] = cleaned["date"].dt.strftime("%Y-%m-%d")
    return cleaned


def latest_prices(cleaned: pd.DataFrame, crop: str, kind: str = "estimated") -> pd.DataFrame:
    """Return latest available price per real market. No aggregation mixing."""
    sub = cleaned.loc[(cleaned["crop"] == crop) & (cleaned["price_kind"] == kind)].copy()
    if sub.empty:
        return sub
    sub["date"] = pd.to_datetime(sub["date"])
    sub = sub.sort_values("date").drop_duplicates("market_id", keep="last")
    return sub.sort_values("market").reset_index(drop=True)


def describe_dataset(prices: pd.DataFrame) -> dict:
    rows = []
    for crop in CROPS:
        for kind in ["observed", "estimated"]:
            data = prices[(prices.crop == crop) & (prices.price_kind == kind)]
            rows.append({"crop": crop, "kind": kind, "records": int(len(data)), "markets": int(data.market_id.nunique()), "first": str(data.date.min()) if not data.empty else "", "last": str(data.date.max()) if not data.empty else ""})
    return {"rows": int(len(prices)), "states": int(prices.state.nunique()), "markets": int(prices.market_id.nunique()), "source": "World Bank Real-Time Food Prices Nigeria, version 2026-10-05", "notes": "RTFP estimated monthly closing prices are MODEL ESTIMATES, not live observed quotes.", "crop_coverage": rows}
