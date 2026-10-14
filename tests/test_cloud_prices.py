"""Private Supabase reads: no real credentials or network are needed."""
import pytest
import requests

from src.cloud_prices import CloudPriceError, fetch_private_prices

URL = "https://exampleabc.supabase.co"
KEY = "sb_publishable_sample_key"
EMAIL = "reader@example.org"
PASSWORD = "test-password-not-real"


class DummyResponse:
    def __init__(self, content, status_error=None):
        self.content = content
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.content


def row(number):
    return {
        "id": number, "date": "2026-10-01", "crop": "Maize",
        "market_id": f"m{number}", "market": f"Market {number}",
        "state": "Kaduna", "latitude": 10.0, "longitude": 8.0,
        "price_ngn_per_kg": 400 + number, "price_kind": "estimated",
    }


def test_authentication_and_private_paginated_reads():
    sample = [row(i) for i in range(1, 6)]
    calls = []

    def mock_post(url, *, params, json, headers, timeout):
        assert url == URL + "/auth/v1/token"
        assert params == {"grant_type": "password"}
        assert json == {"email": EMAIL, "password": PASSWORD}
        assert headers["apikey"] == KEY
        assert timeout == 20
        return DummyResponse({"access_token": "short-lived-test-jwt"})

    def mock_get(url, *, params, headers, timeout):
        assert url == URL + "/rest/v1/prices"
        assert headers["apikey"] == KEY
        assert headers["Authorization"] == "Bearer short-lived-test-jwt"
        assert timeout == 20
        offset, limit = int(params["offset"]), int(params["limit"])
        calls.append(offset)
        return DummyResponse(sample[offset:offset + limit])

    data = fetch_private_prices(
        URL, KEY, EMAIL, PASSWORD, page_size=2,
        post=mock_post, get=mock_get,
    )
    assert calls == [0, 2, 4]
    assert len(data) == 5
    assert data.market_id.tolist() == ["m1", "m2", "m3", "m4", "m5"]


def test_no_access_without_user_session():
    def mock_post(url, *, params, json, headers, timeout):
        return DummyResponse({})

    with pytest.raises(CloudPriceError, match="no access token"):
        fetch_private_prices(URL, KEY, EMAIL, PASSWORD, post=mock_post)


def test_denied_rls_does_not_return_rows():
    def mock_post(url, *, params, json, headers, timeout):
        return DummyResponse({"access_token": "test-jwt"})

    def mock_get(url, *, params, headers, timeout):
        return DummyResponse([])

    with pytest.raises(CloudPriceError, match="No private price rows visible"):
        fetch_private_prices(URL, KEY, EMAIL, PASSWORD, post=mock_post, get=mock_get)


def test_failed_auth_error_does_not_echo_password():
    def mock_post(url, *, params, json, headers, timeout):
        return DummyResponse({}, requests.HTTPError("do not propagate"))

    with pytest.raises(CloudPriceError) as exc:
        fetch_private_prices(URL, KEY, EMAIL, PASSWORD, post=mock_post)
    assert PASSWORD not in str(exc.value)
    assert "authentication failed" in str(exc.value)


@pytest.mark.parametrize("unsafe_key", ["sb_secret_12345", "legacy-service-jwt-key"])
def test_privileged_keys_rejected(unsafe_key):
    with pytest.raises(CloudPriceError, match="publishable"):
        fetch_private_prices(URL, unsafe_key, EMAIL, PASSWORD)


@pytest.mark.parametrize("unsafe_url", [
    "http://localhost:8000", "https://example.supabase.co.evil.com",
    "https://example.supabase.co/path", "https://example.supabase.co@evil.net",
])
def test_invalid_url_rejected(unsafe_url):
    with pytest.raises(CloudPriceError, match="Invalid Supabase"):
        fetch_private_prices(unsafe_url, KEY, EMAIL, PASSWORD)


def test_reader_credentials_required():
    with pytest.raises(CloudPriceError, match="required"):
        fetch_private_prices(URL, KEY, "", "")


def test_duplicate_rows_rejected():
    a, b = row(1), row(2)
    b["market_id"] = a["market_id"]

    def mock_post(url, *, params, json, headers, timeout):
        return DummyResponse({"access_token": "test-jwt"})

    def mock_get(url, *, params, headers, timeout):
        return DummyResponse([a, b])

    with pytest.raises(CloudPriceError, match="duplicate price keys"):
        fetch_private_prices(URL, KEY, EMAIL, PASSWORD, post=mock_post, get=mock_get)
