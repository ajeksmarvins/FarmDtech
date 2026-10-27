
"""FarmDtech API for the Lovable frontend."""

import os

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.cloud_prices import fetch_readonly_prices, CloudPriceError

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="FarmDtech API",
    description="Historical crop-price intelligence and market data.",
    version="1.0.0",
)


# Temporary development setting. We'll restrict this to your frontend URL
# before production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "app": "FarmDtech API",
        "status": "running",
        "note": "Prices are historical or model-estimated, not live quotes.",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/prices")
def prices(crop: str | None = Query(default=None)):
    """Return historical prices from Supabase using read-only access."""
    project_url = os.getenv("SUPABASE_URL", "")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not project_url or not service_role_key:
        raise HTTPException(
            status_code=503,
            detail="Supabase read-only configuration is missing.",
        )

    
    try:
        df = fetch_readonly_prices(project_url, service_role_key)
    except CloudPriceError as exc:
        print("Supabase read error:", repr(exc), flush=True)
        raise HTTPException(
            status_code=502,
            detail=f"Supabase read failed: {exc}",
        )


    if crop:
        df = df[df["crop"].astype(str).str.casefold() == crop.casefold()]

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.astype(object).where(pd.notna(df), None)

    return {
        "count": len(df),
        "source": "Supabase historical price data",
        "is_live_market_data": False,
        "prices": df.to_dict(orient="records"),
    }
