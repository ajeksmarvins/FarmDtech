"""Optional notification handoff to an n8n workflow using a private webhook.

A successful webhook request DOES NOT by itself prove SMS delivery. The n8n
workflow must be connected to a delivery provider and verified end-to-end.
"""
import os
import requests


def format_advice(crop: str, market: str, price_per_kg: float, forecast_month: str, is_estimate: bool = True) -> str:
    label = 'estimated' if is_estimate else 'observed'
    return (f"FarmDtech: {crop} at {market} is NGN {price_per_kg:,.0f}/kg "
            f"({label}, data month {forecast_month}). Verify current prices and transport costs before selling.")


def send_to_n8n(payload: dict, webhook_url: str | None = None, token: str | None = None) -> dict:
    url = webhook_url or os.getenv("N8N_WEBHOOK_URL", "")
    if not url or not url.startswith('https://'):
        raise ValueError("N8N_WEBHOOK_URL must be a configured HTTPS endpoint")
    token = token or os.getenv("N8N_WEBHOOK_TOKEN", "")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-FarmDtech-Token"] = token
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {"response_text": response.text, "status_code": response.status_code}
