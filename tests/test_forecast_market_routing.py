"""Regression tests for named-market forecast lookup and chat routing."""
import pandas as pd
import api


def test_forecast_context_matches_market_and_month(tmp_path, monkeypatch):
    csv = tmp_path / "forecasts.csv"
    pd.DataFrame([
        dict(crop="maize", market="Dawanau", state="Kano",
             forecast_month="2026-11-01", forecast_ngn_per_kg=510),
        dict(crop="maize", market="Other Market", state="Kano",
             forecast_month="2026-11-01", forecast_ngn_per_kg=900),
        dict(crop="maize", market="Dawanau", state="Kano",
             forecast_month="2026-12-01", forecast_ngn_per_kg=550),
    ]).to_csv(csv, index=False)
    monkeypatch.setattr(api, "FORECAST_FILE", csv)
    answer = api.forecast_context(
        "How much is the predicted price of maize in Dawanau Market, Kano, for November 2026?"
    )
    assert "Dawanau" in answer
    assert "510" in answer
    assert "900" not in answer
    assert "550" not in answer


def test_forecast_context_missing_month_does_not_invent(tmp_path, monkeypatch):
    csv = tmp_path / "forecasts.csv"
    pd.DataFrame([dict(crop="maize", market="Dawanau", state="Kano",
                       forecast_month="2026-11-01", forecast_ngn_per_kg=510)]
                 ).to_csv(csv, index=False)
    monkeypatch.setattr(api, "FORECAST_FILE", csv)
    answer = api.forecast_context("Predict maize in Dawanau for December 2026")
    assert "No saved XGBoost prediction" in answer
    assert "510" not in answer
