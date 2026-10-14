"""Historical weekly dashboard export is explicitly not a current price feed."""
import json
import pandas as pd
import pytest
from scripts.export_weekly_dashboard import export_dashboard
from src.weekly_dashboard import load_historical_backtest


def sample_inputs(tmp_path):
    rows = []
    for crop in ("Maize", "Rice", "Beans"):
        rows.append({
            "crop_name": crop, "state": "Kaduna", "market": "Saminaka",
            "variety": "White", "price_type": "Retail",
            "product_origin": "Local", "week_start": "2024-05-06",
            "price_ngn_per_kg": 400.0,
            "xgboost_forecast_ngn_per_kg": 395.0,
            "last_week_baseline_ngn_per_kg": 410.0,
        })
    source = tmp_path / "forecast.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({
        crop: {"current_price_available": False}
        for crop in ("Maize", "Rice", "Beans")
    }))
    return source, metrics


def test_historical_export_and_reload(tmp_path):
    source, metrics = sample_inputs(tmp_path)
    count, nbytes = export_dashboard(source, metrics, tmp_path / "data/demo")
    assert count == 3 and nbytes > 0
    report, rows = load_historical_backtest(tmp_path)
    assert len(report) == 3
    assert set(rows.crop_name) == {"Maize", "Rice", "Beans"}


def test_reject_current_date_in_historical_report(tmp_path):
    source, metrics = sample_inputs(tmp_path)
    rows = pd.read_csv(source)
    rows["week_start"] = "2026-10-01"
    rows.to_csv(source, index=False)
    with pytest.raises(ValueError, match="HISTORICAL"):
        export_dashboard(source, metrics, tmp_path / "data/demo")


def test_missing_assets_handled_safely(tmp_path):
    reports, data = load_historical_backtest(tmp_path)
    assert reports == {}
    assert data.empty
