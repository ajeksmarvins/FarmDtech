"""Run a reproducible historical weekly forecast backtest (NOT current prices).

From project root: python scripts/train_weekly_forecasts.py
Requires data/processed/fews_weekly_prices.csv (not stored in repository).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.weekly_forecast import weekly_prices, make_weekly_features, evaluate_weekly_crop


def main() -> None:
    source = ROOT / "data/processed/fews_weekly_prices.csv"
    if not source.exists():
        raise SystemExit(f"Missing {source}; see docs/FEWS_WEEKLY_DATA.md")
    prices = pd.read_csv(source, low_memory=False)
    weeks = weekly_prices(prices)
    features = make_weekly_features(weeks)
    outputs, metrics = [], {}
    for crop in ("Maize", "Beans", "Rice"):
        report, results = evaluate_weekly_crop(features, crop)
        metrics[crop] = report
        outputs.append(results)
        print(f"{crop}: model {report['model']['wmape_percent']:.2f}% vs last-week baseline {report['last_week_baseline']['wmape_percent']:.2f}% WMAPE")
    output_dir = ROOT / "data/processed"
    pd.concat(outputs, ignore_index=True).to_csv(output_dir / "weekly_historical_backtest.csv", index=False, float_format="%.4f")
    (ROOT / "models/weekly_historical_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Saved historical weekly backtest and metrics. NO present-day price forecast generated.")


if __name__ == "__main__":
    main()
