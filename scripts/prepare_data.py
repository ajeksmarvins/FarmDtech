"""Prepare World Bank price data into farmer-friendly normalized rows.

Run: python scripts/prepare_data.py
"""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import clean_world_bank, describe_dataset

raw = ROOT / "data/raw/NGA_RTFP_mkt_2007_2026-10-05.csv"
out = ROOT / "data/processed"
out.mkdir(parents=True, exist_ok=True)
if not raw.exists():
    sys.exit(f"Source CSV missing: {raw}")
prices = clean_world_bank(raw)
prices.to_csv(out / "prices_long.csv", index=False, float_format="%.5f")
profile = describe_dataset(prices)
(out / "dataset_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
print(json.dumps(profile, indent=2))
print("Cleaned data written to", out / "prices_long.csv")
