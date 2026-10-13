"""Market comparison from normalized prices and straight-line distances."""
from __future__ import annotations
import math
import pandas as pd


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance: approximate, NOT road-driving distance."""
    a1, o1, a2, o2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = a2 - a1, o2 - o1
    h = math.sin(dlat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


def rank_markets(prices: pd.DataFrame, origin_lat: float, origin_lon: float,
                 quantity_kg: float, cost_per_km_ngn: float,
                 fixed_cost_ngn: float = 0.0, max_distance_km: float = 1000,
                 as_of: str | None = None, stale_after_days: int = 65) -> pd.DataFrame:
    """Sort market options by revenue net of user-entered indicative costs.

    Prices must be for exactly one crop and one price_kind, and have been
    reduced to latest prices per market already.
    """
    if quantity_kg <= 0 or min(cost_per_km_ngn, fixed_cost_ngn) < 0 or max_distance_km <= 0:
        raise ValueError("Quantity and distance must be positive; costs cannot be negative")
    if prices.empty:
        return prices.copy()
    if prices.crop.nunique() != 1 or prices.price_kind.nunique() != 1:
        raise ValueError("Market comparison cannot mix crops or observed and estimated prices")
    p = prices.copy()
    p["distance_km"] = [haversine_km(origin_lat, origin_lon, float(lat), float(lon)) for lat, lon in zip(p.latitude, p.longitude)]
    p = p.loc[p.distance_km <= max_distance_km].copy()
    p["gross_ngn"] = p.price_ngn_per_kg * quantity_kg
    p["transport_ngn"] = p.distance_km * cost_per_km_ngn + fixed_cost_ngn
    p["net_ngn"] = p.gross_ngn - p.transport_ngn
    # Warn about staleness relative to dataset's observation date, not server clock.
    reference = pd.Timestamp(as_of) if as_of else pd.Timestamp.today().normalize()
    p["age_days"] = (reference - pd.to_datetime(p.date)).dt.days.clip(lower=0)
    p["stale"] = p.age_days > stale_after_days
    return p.sort_values("net_ngn", ascending=False).reset_index(drop=True)
