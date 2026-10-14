"""Export small historical-only dashboard assets for Streamlit deployment.

Run from project root AFTER train_weekly_forecasts.py:
    python scripts/export_weekly_dashboard.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.weekly_dashboard import BACKTEST_COLUMNS


def export_dashboard(backtest_file: Path, metrics_file: Path, output: Path):
    rows = pd.read_csv(backtest_file, parse_dates=["week_start"])
    missing = set(BACKTEST_COLUMNS) - set(rows.columns)
    if missing:
        raise ValueError(f"Missing backtest columns: {sorted(missing)}")
    rows = rows[BACKTEST_COLUMNS].dropna(subset=[
        "week_start", "price_ngn_per_kg",
        "xgboost_forecast_ngn_per_kg", "last_week_baseline_ngn_per_kg",
    ])
    if rows.empty or rows.week_start.max() > pd.Timestamp("2024-12-31"):
        raise ValueError("Expected nonempty HISTORICAL FEWS NET backtest through 2024")

    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    for crop in ("Maize", "Rice", "Beans"):
        if crop not in metrics or not any(rows.crop_name.eq(crop)):
            raise ValueError(f"Missing metric or historical rows for {crop}")
        if metrics[crop].get("current_price_available") is not False:
            raise ValueError("Historical predictions cannot be labelled current prices")

    output.mkdir(parents=True, exist_ok=True)
    rows = rows.sort_values(["crop_name", "state", "market", "week_start"])
    rows.to_csv(output / "weekly_backtest_demo.csv", index=False,
                float_format="%.2f", date_format="%Y-%m-%d")
    (output / "weekly_historical_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    return len(rows), (output / "weekly_backtest_demo.csv").stat().st_size


def main():
    source = ROOT / "data/processed/weekly_historical_backtest.csv"
    metrics = ROOT / "models/weekly_historical_metrics.json"
    if not source.exists() or not metrics.exists():
        raise SystemExit("First run python scripts/train_weekly_forecasts.py")
    count, size = export_dashboard(source, metrics, ROOT / "data/demo")
    print(f"Exported {count:,} historical predictions, {size / 1024:.1f} KB")
    print("You may commit the TWO generated data/demo files to GitHub,")
    print("after reviewing them and the source dataset attribution.")


if __name__ == "__main__":
    main()
