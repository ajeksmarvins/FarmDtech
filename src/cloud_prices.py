"""Read-only Supabase market price access for the public FarmDtech dashboard.

Uses ONLY a low-privilege sb_publishable_... key and relies on an RLS SELECT
policy. Never use service-role or sb_secret_ credentials in this code.

All returned prices remain historical/model-estimated (not live market quotes).
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
    """Failure fetching / validating read-only cloud price data."""


def fetch_readonly_prices(
    project_url: str,
    publishable_key: str,
    *,
    page_size: int = 1000,
    get=None,
) -> pd.DataFrame:
    """Paginate a stable, read-only Supabase PostgREST query.

    The project's RLS SELECT policy and table grants must permit anonymous
    reads. Fail closed on missing permissions or incomplete result sets.
    """
    project_url = project_url.strip().rstrip("/")
    host = urlparse(project_url)
    if (host.scheme != "https" or host.port is not None or
            not re.fullmatch(r"[a-z0-9-]+\.supabase\.co", host.hostname or "") or
            host.path or host.query or host.fragment or host.username or host.password):
        raise CloudPriceError("Invalid Supabase project URL")
    if not publishable_key.startswith("sb_publishable_"):
        raise CloudPriceError("Use a Supabase publishable (read-only RLS) key, NEVER a secret/service-role key")
    if not 1 <= page_size <= 1000:
        raise ValueError("Page size must be between 1 and 1000")

    getter = get or requests.get
    endpoint = project_url + "/rest/v1/prices"
    headers = {"apikey": publishable_key, "Accept": "application/json"}
    data: list[dict] = []
    previous_id = 0

    for page in range(MAX_PAGES):
        offset = page * page_size
        try:
            response = getter(
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
            # Do not include response bodies or credentials in errors shown to users.
            raise CloudPriceError("Supabase price request failed; check API access and connectivity") from exc

        if not isinstance(batch, list):
            raise CloudPriceError("Unexpected Supabase response format")
        if page == 0 and not batch:
            raise CloudPriceError("Supabase returned no visible price rows; check anon SELECT grant and RLS policy")
        if len(batch) > page_size:
            raise CloudPriceError("Supabase page unexpectedly exceeded requested size")

        for item in batch:
            if not isinstance(item, dict) or not set(["id"] + COLUMNS).issubset(item):
                raise CloudPriceError("Supabase price response is missing required columns")
            try:
                row_id = int(item["id"])
            except (TypeError, ValueError) as exc:
                raise CloudPriceError("Supabase returned an invalid row identifier") from exc
            if row_id <= previous_id:
                raise CloudPriceError("Out-of-order or duplicated cloud price rows")
            previous_id = row_id
            data.append({column: item[column] for column in COLUMNS})

        if len(batch) < page_size:
            break
    else:
        raise CloudPriceError("Exceeded maximum Supabase pages; refusing incomplete data")

    rows = pd.DataFrame(data, columns=COLUMNS)
    rows["date"] = pd.to_datetime(rows["date"], errors="coerce")
    for name in ("latitude", "longitude", "price_ngn_per_kg"):
        rows[name] = pd.to_numeric(rows[name], errors="coerce")
    if rows.empty or rows["date"].isna().any() or rows["price_ngn_per_kg"].isna().any():
        raise CloudPriceError("Missing date or price in Supabase response")
    if rows.duplicated(["date", "crop", "market_id", "price_kind"]).any():
        raise CloudPriceError("Supabase returned duplicate market-date-crop-price type rows")
    return rows
