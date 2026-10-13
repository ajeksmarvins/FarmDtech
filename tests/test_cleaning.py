import pandas as pd
import pytest
from src.cleaning import CROPS, clean_world_bank, latest_prices


def tiny():
    return pd.DataFrame({"geo_id": ["m1", "m1", "m2"], "price_date": ["2026-01-01", "2026-02-01", "2026-01-01"],
        "adm1_name": ["Kano", "Kano", "National Average"], "mkt_name": ["Market A", "Market A", "Abuja"],
        "lat": [12.0, 12.0, 9.0], "lon": [8.0, 8.0, 7.0], "currency": ["NGN"] * 3,
        "beans": [500, None, 750], "c_beans": [550, 625, 730],
        "maize_fao": [200, 210, 220], "c_maize_fao": [205, 215, 225],
        "rice_fao": [1000, 1200, 1400], "c_rice_fao": [1050, 1250, 1350],
        "index_confidence_score": [.8,.9,.9], "data_coverage_recent": [30, 40, 60]})


def test_basket_converts_to_per_kilo():
    cleaned = clean_world_bank(tiny())
    row = cleaned.query("crop == 'Beans' and price_kind == 'observed'").iloc[0]
    assert row.price_ngn_per_kg == 200  # 500 / 2.5 kilograms
    assert row.original_unit_kg == 2.5


def test_observed_and_estimated_stay_distinct():
    cleaned = clean_world_bank(tiny())
    assert len(cleaned[(cleaned.crop == 'Beans') & (cleaned.price_kind == 'observed')]) == 1
    assert len(cleaned[(cleaned.crop == 'Beans') & (cleaned.price_kind == 'estimated')]) == 2
    assert cleaned.state.nunique() == 1


def test_latest_price():
    prices = latest_prices(clean_world_bank(tiny()), 'Maize')
    assert len(prices) == 1
    assert prices.iloc[0].price_ngn_per_kg == 215


def test_requires_columns():
    with pytest.raises(ValueError):
        clean_world_bank(pd.DataFrame({"A": [1]}))
