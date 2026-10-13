"""Leakage-conscious next-MONTH forecasting for World Bank estimated data.

Scores are against *held-out estimated monthly prices*, not independent
observed farm-gate market prices. Weekly forecasting is out of scope.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

FEATURES = ["latitude", "longitude", "month_sin", "month_cos", "lag1", "lag2", "lag3", "mean3", "range3", "trend3"]


def make_features(prices: pd.DataFrame, crop: str) -> pd.DataFrame:
    sub = prices[(prices.crop == crop) & (prices.price_kind == "estimated")].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["date"] = pd.to_datetime(sub["date"])
    sub = sub.sort_values(["market_id", "date"])
    g = sub.groupby("market_id")["price_ngn_per_kg"]
    for n in (1, 2, 3):
        sub[f"lag{n}"] = g.shift(n)
    sub["mean3"] = sub[["lag1", "lag2", "lag3"]].mean(axis=1)
    sub["range3"] = sub[["lag1", "lag2", "lag3"]].max(axis=1) - sub[["lag1", "lag2", "lag3"]].min(axis=1)
    sub["trend3"] = sub["lag1"] - sub["lag3"]
    sub["month_sin"] = np.sin(2 * np.pi * sub.date.dt.month / 12)
    sub["month_cos"] = np.cos(2 * np.pi * sub.date.dt.month / 12)
    return sub.dropna(subset=FEATURES + ["price_ngn_per_kg"])


def evaluate(y_true: np.ndarray, predictions: np.ndarray) -> dict:
    truth, pred = np.asarray(y_true, dtype=float), np.asarray(predictions, dtype=float)
    return {"mae_ngn_per_kg": round(float(np.mean(np.abs(truth - pred))), 2),
            "wmape_percent": round(float(100 * np.sum(np.abs(truth - pred)) / max(np.sum(np.abs(truth)), 1e-9)), 2),
            "n_test": int(len(truth))}


def train_crop(prices: pd.DataFrame, crop: str, holdout_months: int = 6) -> tuple[object, dict]:
    features = make_features(prices, crop)
    if features.empty or features.date.nunique() < 18:
        raise ValueError(f"Not enough monthly history to train {crop}")
    dates = sorted(features.date.unique())
    cutoff = dates[-holdout_months]
    train = features[features.date < cutoff]
    test = features[features.date >= cutoff]
    if len(train) < 100 or len(test) < 10:
        raise ValueError("Not enough train/test observations")
    model = XGBRegressor(n_estimators=175, max_depth=4, learning_rate=0.065,
                         subsample=0.9, colsample_bytree=0.9, reg_lambda=8,
                         tree_method="hist", n_jobs=2, random_state=42)
    # Train on log prices to reduce influence of high price outliers.
    model.fit(train[FEATURES], np.log1p(train.price_ngn_per_kg))
    predictions = np.maximum(0, np.expm1(model.predict(test[FEATURES])))
    baseline = test.lag1.to_numpy(dtype=float)
    result = {"crop": crop,
              "data_source": "World Bank RTFP estimated monthly closing prices",
              "evaluation_target": "held-out model-estimated prices (not independent observed price validation)",
              "forecast_horizon": "next month",
              "train_last_month": str(train.date.max().date()),
              "test_first_month": str(test.date.min().date()),
              "test_last_month": str(test.date.max().date()),
              "model": evaluate(test.price_ngn_per_kg, predictions),
              "naive_last_month_baseline": evaluate(test.price_ngn_per_kg, baseline)}
    # Refit model using ALL available observations for next-month inference.
    model.fit(features[FEATURES], np.log1p(features.price_ngn_per_kg))
    result["trained_through"] = str(features.date.max().date())
    return model, result


def forecast_next_month(prices: pd.DataFrame, crop: str, model) -> pd.DataFrame:
    sub = prices[(prices.crop == crop) & (prices.price_kind == "estimated")].copy()
    sub["date"] = pd.to_datetime(sub["date"])
    sub = sub.sort_values(["market_id", "date"])
    records = []
    for market_id, g in sub.groupby("market_id"):
        if len(g) < 3:
            continue
        end = g.iloc[-1]
        vals = g.price_ngn_per_kg.to_numpy(dtype=float)[-3:]
        next_month = (end.date + pd.offsets.MonthBegin(1)).normalize()
        f = {"latitude": end.latitude, "longitude": end.longitude,
             "month_sin": np.sin(2 * np.pi * next_month.month / 12),
             "month_cos": np.cos(2 * np.pi * next_month.month / 12),
             "lag1": vals[-1], "lag2": vals[-2], "lag3": vals[-3],
             "mean3": float(vals.mean()), "range3": float(vals.max() - vals.min()),
             "trend3": float(vals[-1] - vals[-3])}
        records.append({**f, "market_id": market_id, "market": end.market,
                        "state": end.state, "forecast_month": next_month.strftime("%Y-%m-%d"),
                        "last_month": str(end.date.date()), "last_price_ngn_per_kg": vals[-1]})
    if not records:
        return pd.DataFrame()
    result = pd.DataFrame(records)
    result["forecast_ngn_per_kg"] = np.maximum(0, np.expm1(model.predict(result[FEATURES])))
    result["change_percent"] = 100 * (result.forecast_ngn_per_kg / result.last_price_ngn_per_kg - 1)
    return result.drop(columns=FEATURES).sort_values("market").reset_index(drop=True)
