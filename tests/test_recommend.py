import pandas as pd
import pytest
from src.recommend import haversine_km, rank_markets


def example():
    return pd.DataFrame({"crop": ["Maize", "Maize"], "price_kind": ["estimated", "estimated"],
        "market_id": ["m1", "m2"], "market": ["Near", "Far"], "state": ["A", "B"],
        "latitude": [10, 11], "longitude": [8, 8], "date": ["2026-10-01", "2026-10-01"],
        "price_ngn_per_kg": [300, 350]})


def test_distance():
    assert haversine_km(10, 8, 10, 8) == pytest.approx(0)
    assert 109 < haversine_km(10, 8, 11, 8) < 112


def test_ranking_transport_effect():
    prices = example()
    cheap = rank_markets(prices, 10, 8, 1000, 0, 0, 300, as_of="2026-10-13")
    assert cheap.iloc[0].market == "Far"
    costly = rank_markets(prices, 10, 8, 1000, 1000, 0, 300, as_of="2026-10-13")
    assert costly.iloc[0].market == "Near"


def test_no_mixed_evidence():
    prices = example()
    prices.loc[1, 'price_kind'] = 'observed'
    with pytest.raises(ValueError):
        rank_markets(prices, 10, 8, 100, 100)
