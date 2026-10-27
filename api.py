
"""FarmDtech API.

Historical crop prices and saved next-month forecasts
for the FarmDtech frontend.
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.cloud_prices import (
    CloudPriceError,
    fetch_readonly_prices,
)


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

FORECAST_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "next_month_forecasts.csv"
)


app = FastAPI(
    title="FarmDtech API",
    description=(
        "Historical crop-price intelligence "
        "and model-generated monthly forecasts."
    ),
    version="1.1.0",
)


# CORS configuration for FarmDtech
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "https://farm-dtech-web.vercel.app,https://farmdtech.bolt.host,http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://[a-zA-Z0-9-]+\.local-credentialless\.webcontainer-api\.io",
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "app": "FarmDtech API",
        "status": "running",
        "version": "1.1.0",
        "note": (
            "Prices are historical or estimated. "
            "Forecasts are model-generated predictions, "
            "not live market quotes."
        ),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/prices")
def prices(crop: str | None = Query(default=None)):
    """Return historical prices from Supabase."""

    project_url = os.getenv("SUPABASE_URL", "")
    service_role_key = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    )

    if not project_url or not service_role_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase read-only configuration "
                "is missing."
            ),
        )

    try:
        df = fetch_readonly_prices(
            project_url,
            service_role_key,
        )

    except CloudPriceError as exc:
        print(
            "Supabase read error:",
            repr(exc),
            flush=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve price data.",
        ) from exc

    if crop:
        df = df[
            df["crop"].astype(str).str.casefold()
            == crop.casefold()
        ]

    df = df.copy()

    df["date"] = pd.to_datetime(
        df["date"]
    ).dt.strftime("%Y-%m-%d")

    df = df.astype(object).where(
        pd.notna(df), None
    )

    return {
        "count": len(df),
        "source": "Supabase historical price data",
        "is_live_market_data": False,
        "prices": df.to_dict(orient="records"),
    }


@app.get("/forecast")
def get_forecast(
    crop: str | None = Query(default=None),
):
    """Return saved next-month crop price forecasts."""

    if not FORECAST_FILE.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "Forecast data is not available. "
                "The saved forecast CSV is missing."
            ),
        )

    try:
        df = pd.read_csv(FORECAST_FILE)

    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(
            "Forecast read error:",
            repr(exc),
            flush=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to load forecast data.",
        ) from exc

    required_columns = {
        "crop",
        "market",
        "state",
        "forecast_month",
        "last_month",
        "last_price_ngn_per_kg",
        "forecast_ngn_per_kg",
        "change_percent",
    }

    if not required_columns.issubset(df.columns):
        raise HTTPException(
            status_code=500,
            detail="Forecast file has missing columns.",
        )

    if crop:
        df = df[
            df["crop"].astype(str).str.casefold()
            == crop.casefold()
        ]

    df = df.copy()

    # Replace NaN values with JSON-compatible nulls.
    df = df.astype(object).where(
        pd.notna(df), None
    )

    return {
        "count": len(df),
        "forecast_type": "Next-month XGBoost prediction",
        "source": "Saved FarmDtech model forecasts",
        "is_live_market_data": False,
        "forecast_months": sorted(
            df["forecast_month"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
        "disclaimer": (
            "Forecasts are based on historical "
            "model-estimated prices. They are not "
            "guaranteed future prices or independently "
            "validated live market quotes."
        ),
        "forecasts": df.to_dict(orient="records"),
    }
