"""No network or credentials needed: test read-only paginated Supabase prices."""
import pytest
from src.cloud_prices import CloudPriceError, fetch_readonly_prices

URL = "https://exampleabc.supabase.co"
KEY = "sb_publishable_sample_not_a_secret"

class DummyResponse:
    def __init__(self, rows):
        self.rows = rows

    def raise_for_status(self):
        return None

    def json(self):
        return self.rows


def price_row(i):
    return {
        "id": i, "date": "2026-10-01", "crop": "Maize",
        "market_id": f"m{i}", "market": f"Market {i}",
        "state": "Kaduna", "latitude": 10.0, "longitude": 8.0,
        "price_ngn_per_kg": 400.0 + i, "price_kind": "estimated",
    }


def test_paginated_prices_are_complete_and_sorted():
    all_rows = [price_row(i) for i in range(1, 6)]
    calls = []

    def fake_get(url, *, params, headers, timeout):
        assert url == URL + "/rest/v1/prices"
        assert headers["apikey"] == KEY
        assert "Authorization" not in headers
        assert timeout == 20
        calls.append(int(params["offset"]))
        offset, limit = int(params["offset"]), int(params["limit"])
        return DummyResponse(all_rows[offset:offset+limit])

    result = fetch_readonly_prices(URL, KEY, page_size=2, get=fake_get)
    assert len(result) == 5
    assert calls == [0, 2, 4]
    assert result.market_id.tolist() == ["m1", "m2", "m3", "m4", "m5"]


def test_empty_result_requires_rls_policy():
    def fake_get(url, *, params, headers, timeout):
        return DummyResponse([])

    with pytest.raises(CloudPriceError, match="no visible"):
        fetch_readonly_prices(URL, KEY, get=fake_get)


def test_service_role_and_secret_rejected():
    with pytest.raises(CloudPriceError, match="publishable"):
        fetch_readonly_prices(URL, "sb_secret_any_very_powerful_value")
    with pytest.raises(CloudPriceError, match="publishable"):
        fetch_readonly_prices(URL, "eyJ_service_role_legacy")


def test_invalid_url_rejected():
    with pytest.raises(CloudPriceError, match="Invalid"):
        fetch_readonly_prices("http://localhost", KEY)
    with pytest.raises(CloudPriceError, match="Invalid"):
        fetch_readonly_prices("https://example.supabase.co.attacker.net", KEY)


def test_duplicate_market_date_rows_rejected():
    a, b = price_row(1), price_row(2)
    b["market_id"] = a["market_id"]
    def fake_get(url, *, params, headers, timeout):
        return DummyResponse([a, b])

    with pytest.raises(CloudPriceError, match="duplicate"):
        fetch_readonly_prices(URL, KEY, get=fake_get)
