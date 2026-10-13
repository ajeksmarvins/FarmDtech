"""Train three models using chronological validation, save forecasts and metrics.

Run: python scripts/train_models.py
"""
import json
import sys
from pathlib import Path
import joblib
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.forecast import train_crop, forecast_next_month
from src.cleaning import CROPS

source = ROOT / "data/processed/prices_long.csv"
if not source.exists():
    sys.exit("Please run python scripts/prepare_data.py first")
prices = pd.read_csv(source, low_memory=False)
models = ROOT / "models"
models.mkdir(parents=True, exist_ok=True)
reports = {}
forecast_rows = []
for crop in CROPS:
    print(f"Training {crop} ...", flush=True)
    model, report = train_crop(prices, crop)
    joblib.dump(model, models / f"{crop.lower()}_xgb.joblib")
    reports[crop] = report
    predictions = forecast_next_month(prices, crop, model)
    predictions.insert(0, "crop", crop)
    forecast_rows.append(predictions)
    print(json.dumps(report, indent=2))
(models / "metrics.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
pd.concat(forecast_rows, ignore_index=True).to_csv(ROOT / "data/processed/next_month_forecasts.csv", index=False, float_format="%.4f")
print("Models and forecasts saved.")
