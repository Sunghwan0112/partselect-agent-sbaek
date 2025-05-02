import os
import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": BRAVE_API_KEY,
}

# Simple in-memory cache to prevent repeated rate-limited requests
_brave_cache = {}

def brave_search(query: str, site_filter: str = "partselect.com", limit: int = 5) -> list:
    if query in _brave_cache:
        return _brave_cache[query]

    try:
        params = {
            "q": f"{query} site:{site_filter}",
            "count": limit,
            "search_lang": "en",
        }
        response = requests.get(BRAVE_API_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("web", {}).get("results", [])
        _brave_cache[query] = results
        return results
    except Exception as e:
        print(f"Brave search failed: {e}")
        return []

def search_partselect(query: str) -> Optional[dict]:
    results = brave_search(query)
    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        snippet = r.get("description", "")
        if "partselect.com" in url and "PS" in url:
            return {
                "title": title,
                "url": url,
                "snippet": snippet,
            }
    return None



