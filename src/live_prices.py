"""Fetch dated, indicative Nigerian commodity prices from a public source.

This is a NATIONAL reference feed, not a verified offer at a named market.
No missing prices, locations or observation dates are invented.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock
import time
import re

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.rolglobaltrade.com/commodity-prices.php"
SUPPORTED = {"maize": "maize", "rice paddy": "rice", "rice": "rice", "beans": "beans"}
MAX_AGE_DAYS = 14
CACHE_TTL_SECONDS = 900
_cache_lock = Lock()
_cache_records = None
_cache_expiry = 0.0


class PriceSourceError(RuntimeError):
    """The publisher could not be reached or its data could not be validated."""


def _number(text: str) -> Decimal | None:
    cleaned = re.sub(r"[^0-9.]", "", text.split("—")[0])
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def parse_prices(html: str, *, checked_at: datetime | None = None) -> list[dict]:
    """Parse published table rows; keep only dated, unit-explicit prices."""
    checked_at = checked_at or datetime.now(timezone.utc)
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for table in soup.find_all("table"):
        headers = [" ".join(th.stripped_strings).casefold() for th in table.find_all("tr")[0].find_all(["th", "td"])] if table.find("tr") else []
        if not (any("commodity" in h for h in headers) and any("source date" in h for h in headers)):
            continue
        def idx(term):
            return next((i for i, h in enumerate(headers) if term in h), None)
        commodity_i, date_i, source_i = idx("commodity"), idx("source date"), idx("source")
        price_i = next((i for i, h in enumerate(headers) if "price / mt" in h or "price/mt" in h), None)
        if price_i is None:
            continue
        for tr in table.find_all("tr")[1:]:
            cells = [" ".join(td.stripped_strings) for td in tr.find_all(["td", "th"], recursive=False)]
            if len(cells) < len(headers):
                continue
            label = cells[commodity_i].strip().casefold()
            crop = SUPPORTED.get(label)
            amount = _number(cells[price_i])
            if not crop or amount is None:
                continue
            try:
                observed = datetime.strptime(cells[date_i].strip(), "%d %b %Y").date()
            except ValueError:
                continue
            age = (checked_at.date() - observed).days
            if age < 0:
                continue
            records.append({
                "crop": crop,
                "commodity_label": cells[commodity_i].strip(),
                "price_ngn_per_kg": float(amount / Decimal(1000)),
                "unit": "NGN/kg",
                "original_price_ngn_per_metric_tonne": float(amount),
                "geographic_scope": "Nigeria (national indicative reference; market unspecified)",
                "market": None,
                "state": None,
                "observed_date": observed.isoformat(),
                "checked_at": checked_at.isoformat(),
                "publisher": "ROL Global",
                "underlying_source": cells[source_i].strip() if source_i is not None else None,
                "source_url": SOURCE_URL,
                "data_type": "published_indicative_price",
                "is_forecast": False,
                "is_named_market_quote": False,
                "is_recent": age <= MAX_AGE_DAYS,
            })
    if not records:
        raise PriceSourceError("No valid dated commodity rows found; publisher layout may have changed.")
    return records


def fetch_prices(timeout: int = 12) -> list[dict]:
    """Cache successful fetches for 15 minutes; never cache a failure."""
    global _cache_records, _cache_expiry
    with _cache_lock:
        if _cache_records is not None and time.monotonic() < _cache_expiry:
            return [dict(record) for record in _cache_records]
        try:
            response = requests.get(
                SOURCE_URL,
                timeout=timeout,
                headers={"User-Agent": "FarmDtechResearch/1.0 (educational price attribution)"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise PriceSourceError("Publisher unavailable.") from exc
        records = parse_prices(response.text)
        _cache_records = records
        _cache_expiry = time.monotonic() + CACHE_TTL_SECONDS
        return [dict(record) for record in records]
