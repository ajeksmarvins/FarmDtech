"""Historical weekly price backtesting with strict calendar-week lag features.

This dataset ends in May 2024. Predictions from this module are research
backtests, NOT 2026 market quotes, live alerts or production price forecasts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

SERIES = ["state", "market", "crop", "variety", "price_type", "product_origin"]
LAGS = ["lag1", "lag2", "lag3", "lag4"]
NUMERIC = LAGS + ["mean4", "change4", "std4", "month_sin", "month_cos", "latitude", "longitude"]
CATEGORICAL = ["state", "market", "variety", "price_type", "product_origin"]


def weekly_prices(raw: pd.DataFrame) -> pd.DataFrame:
    """Make one median NGN/kg observation per week & like-for-like series."""
    required = set(SERIES + ["date", "price_ngn_per_kg", "latitude", "longitude", "price_kind"])
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing weekly data fields: {sorted(missing)}")
    df = raw.loc[raw.price_kind.eq("reported_historical")].copy()
    df["date"] = pd.to_datetime(df.date, errors="coerce")
    df["price_ngn_per_kg"] = pd.to_numeric(df.price_ngn_per_kg, errors="coerce")
    df = df.loc[df.date.notna() & df.price_ngn_per_kg.gt(0)].copy()
    df["week_start"] = df.date.dt.to_period("W-SUN").dt.start_time
    weekly = df.groupby(SERIES + ["week_start"], as_index=False, dropna=False).agg(
        price_ngn_per_kg=("price_ngn_per_kg", "median"),
        latitude=("latitude", "median"), longitude=("longitude", "median"),
        observations_in_week=("date", "size"),
    )
    return weekly.sort_values(SERIES + ["week_start"]).reset_index(drop=True)


def make_weekly_features(weekly: pd.DataFrame) -> pd.DataFrame:
    """Train on price in week T, using only T-1 to T-4 calendar-week prices.

    Missing intermediate weeks are never silently treated as consecutive ones.
    Actual earlier observed prices can enter a held-out week's features, as in a
    rolling one-step-ahead forecast updated each week.
    """
    if weekly.empty:
        return weekly.copy()
    df = weekly.copy()
    df["week_start"] = pd.to_datetime(df.week_start)
    if df.duplicated(SERIES + ["week_start"]).any():
        raise ValueError("Multiple price rows for the same commodity-market-week series")
    for n in range(1, 5):
        lag = df[SERIES + ["week_start", "price_ngn_per_kg"]].copy()
        lag["week_start"] = lag.week_start + pd.to_timedelta(n * 7, unit='D')
        lag = lag.rename(columns={"price_ngn_per_kg": f"lag{n}"})
        df = df.merge(lag, on=SERIES + ["week_start"], how="left", validate="one_to_one")
    df = df.dropna(subset=LAGS).copy()
    df["mean4"] = df[LAGS].mean(axis=1)
    df["std4"] = df[LAGS].std(axis=1, ddof=0)
    df["change4"] = df.lag1 - df.lag4
    df["month_sin"] = np.sin(2 * np.pi * df.week_start.dt.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df.week_start.dt.month / 12)
    return df.sort_values(["week_start"] + SERIES).reset_index(drop=True)


def split_chronologically(features: pd.DataFrame, test_weeks: int = 26):
    """Hold out the last N calendar weeks, not a random train/test shuffle."""
    if features.empty:
        raise ValueError("No continuous four-week histories are available")
    cutoff = features.week_start.max() - pd.to_timedelta((test_weeks - 1) * 7, unit='D')
    train = features.loc[features.week_start < cutoff].copy()
    test = features.loc[features.week_start >= cutoff].copy()
    if len(train) < 100 or len(test) < 30:
        raise ValueError("Insufficient past data for chronological evaluation")
    return train, test


def _design(train: pd.DataFrame, test: pd.DataFrame):
    tr = pd.get_dummies(train[NUMERIC + CATEGORICAL], columns=CATEGORICAL, dtype=float)
    te = pd.get_dummies(test[NUMERIC + CATEGORICAL], columns=CATEGORICAL, dtype=float)
    return tr, te.reindex(columns=tr.columns, fill_value=0)


def _metrics(truth: np.ndarray, predicted: np.ndarray) -> dict:
    truth, predicted = np.asarray(truth, float), np.asarray(predicted, float)
    if not len(truth):
        raise ValueError("Cannot evaluate an empty test set")
    return {
        "mae_ngn_per_kg": round(float(np.abs(truth - predicted).mean()), 2),
        "wmape_percent": round(float(100 * np.abs(truth - predicted).sum() / max(np.abs(truth).sum(), 1e-9)), 2),
        "records": int(len(truth)),
    }


def evaluate_weekly_crop(features: pd.DataFrame, crop: str, test_weeks: int = 26):
    subset = features.loc[features.crop.eq(crop)].copy()
    train, test = split_chronologically(subset, test_weeks)
    X_train, X_test = _design(train, test)
    model = XGBRegressor(
        n_estimators=140, max_depth=4, learning_rate=0.06,
        subsample=0.90, colsample_bytree=0.90,
        tree_method="hist", n_jobs=2, random_state=42, reg_lambda=8,
    )
    model.fit(X_train, np.log1p(train.price_ngn_per_kg))
    predicted = np.maximum(0, np.expm1(model.predict(X_test)))
    baseline = test.lag1.to_numpy(dtype=float)
    actual = test.price_ngn_per_kg.to_numpy(dtype=float)
    report = {
        "crop": crop, "forecast_horizon": "one calendar week",
        "data_last_week": str(subset.week_start.max().date()),
        "train_last_week": str(train.week_start.max().date()),
        "test_first_week": str(test.week_start.min().date()),
        "test_last_week": str(test.week_start.max().date()),
        "model": _metrics(actual, predicted),
        "last_week_baseline": _metrics(actual, baseline),
        "evaluation_target": "held-out reported historical FEWS NET weekly prices",
        "current_price_available": False,
        "warning": "Historical only through 2024; scores do not establish 2026 price accuracy",
    }
    outputs = test[SERIES + ["week_start", "latitude", "longitude", "price_ngn_per_kg"]].copy()
    outputs["xgboost_forecast_ngn_per_kg"] = predicted
    outputs["last_week_baseline_ngn_per_kg"] = baseline
    outputs.insert(0, "crop_name", crop)
    return report, outputs.reset_index(drop=True)
