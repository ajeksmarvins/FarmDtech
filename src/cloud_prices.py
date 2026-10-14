"""Private, read-only Supabase price access for the FarmDtech Streamlit SERVER.

Sign in as a dedicated Supabase Auth reader account. Its user UUID is the
*only* one permitted by a read-only SELECT RLS policy on public.prices.

The Supabase publishable key identifies the app but grants no private rows by
itself. NEVER use service_role / sb_secret_ in this dashboard.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import pandas as pd
import requests

COLUMNS = [
    "date", "crop", "market_id", "market", "state", "latitude",
    "longitude", "price_ngn_per_kg", "price_kind",
]
MAX_PAGES = 100


class CloudPriceError(RuntimeError):
    """Failure authenticating, fetching, or validating private cloud prices."""


def _validate(project_url: str, key: str, email: str, password: str) -> str:
    url = project_url.strip().rstrip("/")
    host = urlparse(url)
    if (
        host.scheme != "https"
        or host.port is not None
        or not re.fullmatch(r"[a-z0-9-]+\.supabase\.co", host.hostname or "")
        or host.path or host.query or host.fragment or host.username or host.password
    ):
        raise CloudPriceError("Invalid Supabase project URL")
    if not key.startswith("sb_publishable_"):
        raise CloudPriceError("Only a Supabase publishable key is allowed in the dashboard")
    if not email.strip() or not password:
        raise CloudPriceError("Dedicated reader email and password are required")
    return url


def fetch_private_prices(
    project_url: str,
    publishable_key: str,
    reader_email: str,
    reader_password: str,
    *,
    page_size: int = 1000,
    get=None,
    post=None,
) -> pd.DataFrame:
    """Authenticate server-side, then read price rows as the limited Auth user.

    No access tokens or passwords are exposed to the browser. Requests use
    only this reader's JWT; the Supabase RLS policy authorizes SELECT solely
    for the configured reader UUID.

    The result is historical World Bank data, not real-time buyer prices.
    """
    url = _validate(project_url, publishable_key, reader_email, reader_password)
    if not 1 <= page_size <= 1000:
        raise ValueError("Page size must be between 1 and 1000")

    post_request = post or requests.post
    get_request = get or requests.get

    # Authenticate using a dedicated reader, never a service_role API key.
    try:
        auth_response = post_request(
            url + "/auth/v1/token",
            params={"grant_type": "password"},
            json={"email": reader_email, "password": reader_password},
            headers={"apikey": publishable_key, "Content-Type": "application/json"},
            timeout=20,
        )
        auth_response.raise_for_status()
        auth_payload = auth_response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CloudPriceError("Private Supabase reader authentication failed") from exc
    token = auth_payload.get("access_token") if isinstance(auth_payload, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise CloudPriceError("Private Supabase authentication returned no access token")

    headers = {
        "apikey": publishable_key,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    endpoint = url + "/rest/v1/prices"
    data: list[dict] = []
    previous_id = 0

    for page in range(MAX_PAGES):
        offset = page * page_size
        try:
            response = get_request(
                endpoint,
                params={
                    "select": ",".join(["id"] + COLUMNS),
                    "order": "id.asc",
                    "limit": str(page_size),
                    "offset": str(offset),
                },
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            batch = response.json()
        except (requests.RequestException, ValueError) as exc:
            # Avoid logging tokens, response bodies, or internal auth details.
            raise CloudPriceError("Private Supabase price request failed") from exc

        if not isinstance(batch, list):
            raise CloudPriceError("Unexpected Supabase response format")
        if page == 0 and not batch:
            raise CloudPriceError("No private price rows visible; check reader UUID, grants and RLS")
        if len(batch) > page_size:
            raise CloudPriceError("Supabase returned too many rows for one page")

        for item in batch:
            if not isinstance(item, dict) or not set(["id"] + COLUMNS).issubset(item):
                raise CloudPriceError("Incomplete private price record")
            try:
                row_id = int(item["id"])
            except (TypeError, ValueError) as exc:
                raise CloudPriceError("Invalid Supabase record ID") from exc
            if row_id <= previous_id:
                raise CloudPriceError("Duplicate or out-of-order price rows")
            previous_id = row_id
            data.append({name: item[name] for name in COLUMNS})
        if len(batch) < page_size:
            break
    else:
        raise CloudPriceError("Too many pages; refusing partial data")

    result = pd.DataFrame(data, columns=COLUMNS)
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    for name in ("latitude", "longitude", "price_ngn_per_kg"):
        result[name] = pd.to_numeric(result[name], errors="coerce")
    if (
        result.empty
        or result["date"].isna().any()
        or result["price_ngn_per_kg"].isna().any()
        or (result["price_ngn_per_kg"] <= 0).any()
    ):
        raise CloudPriceError("Supabase returned invalid price/date values")
    if result.duplicated(["date", "crop", "market_id", "price_kind"]).any():
        raise CloudPriceError("Supabase returned duplicate price keys")
    return result
