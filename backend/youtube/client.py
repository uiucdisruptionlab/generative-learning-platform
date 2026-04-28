from __future__ import annotations

import os
import requests
from typing import Any

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def _thumbnail_url(snippet: dict[str, Any]) -> str:
    thumbs = snippet.get("thumbnails") or {}
    for key in ("medium", "high", "standard", "default"):
        t = thumbs.get(key)
        if isinstance(t, dict) and t.get("url"):
            return str(t["url"])
    return ""


def search_videos(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """
    Search YouTube Data API v3 for videos. Returns [] if the API key is missing or the request fails.

    Reads YOUTUBE_API_KEY at call time (not import time) so server startup can load_dotenv first.
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[youtube] YOUTUBE_API_KEY is not set; skipping video search.")
        return []

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": api_key,
        "relevanceLanguage": "en",
        "safeSearch": "strict",
    }

    try:
        response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[youtube] Search request failed: {exc}")
        return []

    items = response.json().get("items", [])
    out: list[dict[str, Any]] = []
    for item in items:
        vid = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not vid or not snippet:
            continue
        title = snippet.get("title") or "Untitled"
        channel = snippet.get("channelTitle") or ""
        desc = snippet.get("description") or ""
        thumb = _thumbnail_url(snippet)
        out.append(
            {
                "video_id": vid,
                "title": title,
                "channel": channel,
                "description": desc,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail": thumb,
            }
        )
        if len(out) >= max_results:
            break

    return out
