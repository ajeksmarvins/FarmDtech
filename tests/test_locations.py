"""Nationwide home-location selection does not fabricate crop-market prices."""
import pandas as pd
from src.locations import STATE_REFERENCE_POINTS, price_state_name, local_net_reference
from src.recommend import rank_markets


def test_all_states_and_fct_supported():
    assert len(STATE_REFERENCE_POINTS) == 37
    assert "FCT (Abuja)" in STATE_REFERENCE_POINTS
    assert "Kaduna" in STATE_REFERENCE_POINTS
    assert "Lagos" in STATE_REFERENCE_POINTS
    assert len(set(STATE_REFERENCE_POINTS)) == 37
    for lat, lon in STATE_REFERENCE_POINTS.values():
        assert 4 <= lat <= 14 and 2 <= lon <= 15


def test_fct_label_mapped_for_same_state_check():
    assert price_state_name("FCT (Abuja)") == "Federal Capital Territory"
    assert price_state_name("Kano") == "Kano"


def test_missing_local_quotes_not_invented():
    data = pd.DataFrame({
        "crop": ["Maize", "Maize"], "price_kind": ["estimated", "estimated"],
        "market_id": ["m1", "m2"], "market": ["Lokoja", "Minna"],
        "state": ["Kogi", "Niger"], "latitude": [7.8, 9.6],
        "longitude": [6.7, 6.55], "date": ["2026-10-01", "2026-10-01"],
        "price_ngn_per_kg": [400.0, 450.0]
    })
    lat, lon = STATE_REFERENCE_POINTS["FCT (Abuja)"]
    ranked = rank_markets(data, lat, lon, 1000, 100, 5000, 1000, as_of="2026-10-13")
    assert len(ranked) == 2
    assert local_net_reference(ranked, "FCT (Abuja)") is None
    assert local_net_reference(ranked, "Niger") == float(ranked.loc[ranked.state == "Niger", "net_ngn"].max())
