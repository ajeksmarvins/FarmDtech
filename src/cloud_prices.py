
"""Read-only Supabase market price access for the FarmDtech backend."""

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
    """Failure fetching or validating cloud price data."""



def fetch_price_page(
    project_url: str,
    service_role_key: str,
    *,
    crop: str = "all",
    state: str = "all",
    search: str = "",
    page: int = 1,
    page_size: int = 12,
    get=None,
) -> tuple[int, list[dict]]:
    """Read one page and an exact count without fetching every historical row."""
    project_url = project_url.strip().rstrip("/")
    host = urlparse(project_url)
    if (
        host.scheme != "https"
        or host.port is not None
        or not re.fullmatch(r"[a-z0-9-]+\.supabase\.co", host.hostname or "")
        or host.path or host.query or host.fragment or host.username or host.password
        or not service_role_key.strip()
    ):
        raise CloudPriceError("Invalid Supabase configuration")

    params = {
        "select": ",".join(COLUMNS),
        "order": "date.desc,id.desc",
        "limit": str(page_size),
        "offset": str((page - 1) * page_size),
    }
    if crop != "all":
        params["crop"] = "eq." + crop
    if state != "all":
        params["state"] = "eq." + state
    term = search.strip()
    if term:
        # Restrict PostgREST filter syntax; user input remains ordinary search text.
        if len(term) > 80 or not re.fullmatch(r"[\w\s-]+", term):
            raise ValueError("Search contains unsupported characters")
        params["or"] = "(" + ",".join(
            f"{column}.ilike.*{term}*" for column in ("crop", "market", "state")
        ) + ")"

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept": "application/json",
        "Prefer": "count=exact",
    }
    try:
        response = (get or requests.get)(
            project_url + "/rest/v1/prices",
            params=params, headers=headers, timeout=20,
        )
        response.raise_for_status()
        rows = response.json()
        content_range = response.headers.get("Content-Range", "")
        count = int(content_range.rsplit("/", 1)[1])
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
        raise CloudPriceError("Unable to retrieve paginated crop prices") from exc
    if not isinstance(rows, list) or len(rows) > page_size:
        raise CloudPriceError("Unexpected paginated crop price response")
    if any(not isinstance(row, dict) or not set(COLUMNS).issubset(row) for row in rows):
        raise CloudPriceError("Paginated crop prices are missing required fields")
    return count, rows

def fetch_readonly_prices(
    project_url: str,
    service_role_key: str,
    *,
    page_size: int = 1000,
    get=None,
) -> pd.DataFrame:
    """Fetch price rows from Supabase using backend-only credentials."""
    project_url = project_url.strip().rstrip("/")
    host = urlparse(project_url)

    if (
        host.scheme != "https"
        or host.port is not None
        or not re.fullmatch(
            r"[a-z0-9-]+\.supabase\.co",
            host.hostname or "",
        )
        or host.path
        or host.query
        or host.fragment
        or host.username
        or host.password
    ):
        raise CloudPriceError("Invalid Supabase project URL")

    if not service_role_key.strip():
        raise CloudPriceError("Supabase service-role key is missing")

    if not 1 <= page_size <= 1000:
        raise ValueError("Page size must be between 1 and 1000")

    getter = get or requests.get
    endpoint = project_url + "/rest/v1/prices"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept": "application/json",
    }

    data = []
    previous_id = 0

    for page in range(MAX_PAGES):
        try:
            response = getter(
                endpoint,
                params={
                    "select": ",".join(["id"] + COLUMNS),
                    "order": "id.asc",
                    "limit": str(page_size),
                    "offset": str(page * page_size),
                },
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            batch = response.json()
        except (requests.RequestException, ValueError) as exc:
            # Keep credentials and response bodies out of public error messages.
            raise CloudPriceError(
                "Supabase price request failed; check the key, table, and connectivity"
            ) from exc

        if not isinstance(batch, list):
            raise CloudPriceError("Unexpected Supabase response format")

        if page == 0 and not batch:
            raise CloudPriceError("Supabase returned no price rows")

        if len(batch) > page_size:
            raise CloudPriceError("Supabase page exceeded requested size")

        for item in batch:
            if not isinstance(item, dict) or not set(
                ["id"] + COLUMNS
            ).issubset(item):
                raise CloudPriceError(
                    "Supabase price response is missing required columns"
                )

            try:
                row_id = int(item["id"])
            except (TypeError, ValueError) as exc:
                raise CloudPriceError(
                    "Supabase returned an invalid row identifier"
                ) from exc

            if row_id <= previous_id:
                raise CloudPriceError(
                    "Out-of-order or duplicated cloud price rows"
                )

            previous_id = row_id
            data.append({column: item[column] for column in COLUMNS})

        if len(batch) < page_size:
            break
    else:
        raise CloudPriceError(
            "Exceeded maximum Supabase pages; refusing incomplete data"
        )

    rows = pd.DataFrame(data, columns=COLUMNS)
    rows["date"] = pd.to_datetime(rows["date"], errors="coerce")

    for name in ("latitude", "longitude", "price_ngn_per_kg"):
        rows[name] = pd.to_numeric(rows[name], errors="coerce")

    if (
        rows.empty
        or rows["date"].isna().any()
        or rows["price_ngn_per_kg"].isna().any()
    ):
        raise CloudPriceError("Missing date or price in Supabase response")

    if rows.duplicated(
        ["date", "crop", "market_id", "price_kind"]
    ).any():
        raise CloudPriceError(
            "Supabase returned duplicate market-date-crop-price type rows"
        )

    return rows
