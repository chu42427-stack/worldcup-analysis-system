from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_FIELDS = {
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation",
    "weather_code",
}


def fetch_open_meteo(latitude: float, longitude: float) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def parse_open_meteo_response(match_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current", {})
    if not isinstance(current, dict):
        current = {}
    has_weather_field = any(field in current for field in WEATHER_FIELDS)
    return {
        "match_id": match_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "wind_kph": current.get("wind_speed_10m"),
        "precipitation_probability": current.get("precipitation"),
        "weather_code": current.get("weather_code"),
        "source_confidence": 1.0 if has_weather_field else 0.0,
    }
