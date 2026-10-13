"""Optional Supabase REST integration; local CSV mode needs no credentials."""
import os
import requests


def upsert_prices(records: list[dict], url: str | None = None, key: str | None = None) -> int:
    """Upsert in chunks. Use a protected service-role key server-side only.

    Do not run this from an untrusted browser/client or commit the secret.
    """
    url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
    key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your environment")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
    total = 0
    for i in range(0, len(records), 300):
        response = requests.post(f"{url}/rest/v1/prices?on_conflict=market_id,crop,date,price_kind",
                                 json=records[i:i + 300], headers=headers, timeout=45)
        response.raise_for_status()
        total += min(300, len(records) - i)
    return total
