"""Hevy API client — fetches and caches all workout data."""

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

CACHE_FILE = Path(__file__).parent / ".hevy_cache.json"
CACHE_MAX_AGE_HOURS = 1


def _request(url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"api-key": api_key, "accept": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    age_hours = (datetime.now().timestamp() - CACHE_FILE.stat().st_mtime) / 3600
    return age_hours < CACHE_MAX_AGE_HOURS


def fetch_all_data(api_key: str, force_refresh: bool = False) -> dict:
    """Return dict with 'workouts' and 'templates', using cache when fresh."""
    if not force_refresh and _cache_valid():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)

    # ── Workouts ──────────────────────────────────────────────────────────
    count = _request("https://api.hevyapp.com/v1/workouts/count", api_key)["workout_count"]
    pages = (count + 9) // 10
    workouts = []
    for page in range(1, pages + 1):
        data = _request(
            f"https://api.hevyapp.com/v1/workouts?page={page}&pageSize=10", api_key
        )
        workouts.extend(data["workouts"])

    # ── Exercise templates (muscle groups) ────────────────────────────────
    first = _request(
        "https://api.hevyapp.com/v1/exercise_templates?page=1&pageSize=100", api_key
    )
    templates = first["exercise_templates"]
    for page in range(2, first["page_count"] + 1):
        data = _request(
            f"https://api.hevyapp.com/v1/exercise_templates?page={page}&pageSize=100",
            api_key,
        )
        templates.extend(data["exercise_templates"])

    result = {"workouts": workouts, "templates": templates}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
