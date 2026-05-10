"""Fetches real-time weather data from wttr.in (free, no API key required)."""
from __future__ import annotations

import re

import requests

_WEATHER_KEYWORDS = re.compile(
    r"\b(weather|temperature|forecast|climate|humidity|rain|sunny|cloudy|hot|cold|warm|wind)\b",
    re.IGNORECASE,
)

_LOCATION_PATTERNS = [
    r"weather\s+(?:of|in|for|at|today\s+in|today\s+at)\s+([A-Za-z][A-Za-z\s,]+?)(?:\s*[?,]|$|\s+today|\s+now|\s+current|\s+india)",
    r"(?:of|in|for|at)\s+([A-Za-z][A-Za-z\s,]+?)\s+weather",
    r"(?:temperature|forecast|climate|rain)\s+(?:of|in|for|at)\s+([A-Za-z][A-Za-z\s,]+?)(?:\s*[?,]|$)",
    r"weather\s+([A-Za-z][A-Za-z\s]+?)(?:\s*[?,]|$|\s+today|\s+now)",
]


def _extract_location(query: str) -> str | None:
    for pattern in _LOCATION_PATTERNS:
        m = re.search(pattern, query, re.IGNORECASE)
        if m:
            loc = m.group(1).strip().rstrip(",").strip()
            skip = {"the", "a", "an", "some", "my", "our", "your", "this", "that"}
            if loc and len(loc) > 1 and loc.lower() not in skip:
                return loc
    return None


def fetch_weather(location: str) -> str | None:
    """Return a formatted current-weather string for the location, or None on failure."""
    try:
        r = requests.get(
            f"https://wttr.in/{location.replace(' ', '+')}",
            params={"format": "j1"},
            timeout=8,
            headers={"User-Agent": "curl/7.68.0"},
        )
        if not r.ok:
            return None
        data = r.json()
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        city = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        return (
            f"Location: {city}, {country}\n"
            f"Condition: {current['weatherDesc'][0]['value']}\n"
            f"Temperature: {current['temp_C']}°C / {current['temp_F']}°F\n"
            f"Feels like: {current['FeelsLikeC']}°C / {current['FeelsLikeF']}°F\n"
            f"Humidity: {current['humidity']}%\n"
            f"Wind: {current['windspeedKmph']} km/h {current['winddir16Point']}\n"
            f"Visibility: {current['visibility']} km"
        )
    except Exception:
        return None


def get_realtime_context(query: str) -> str | None:
    """Return real-time data relevant to the query, or None if not applicable."""
    if not _WEATHER_KEYWORDS.search(query):
        return None
    location = _extract_location(query)
    if not location:
        return None
    return fetch_weather(location)
