from __future__ import annotations

import os
import requests
from typing import Any

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_videos(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Search YouTube for videos matching the query. Returns a list of video metadata."""
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set in environment variables.")

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
        "relevanceLanguage": "en",
        "safeSearch": "strict",
    }

    response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    items = response.json().get("items", [])

    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "description": item["snippet"]["description"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
        }
        for item in items
    ]
