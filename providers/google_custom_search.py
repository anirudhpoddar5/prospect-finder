import re
import requests
from typing import Optional

CSE_URL = "https://www.googleapis.com/customsearch/v1"
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def search_custom(api_key: str, cx: str, query: str, max_results: int = 10) -> list[dict]:
    if not api_key or not cx or not query:
        return []

    results = []
    start = 1

    while len(results) < max_results:
        try:
            resp = requests.get(CSE_URL, params={
                "key": api_key,
                "cx": cx,
                "q": query,
                "start": start,
                "num": min(10, max_results - len(results)),
            }, timeout=10)
        except Exception:
            break

        if resp.status_code != 200:
            break

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            link = item.get("link", "")
            title = item.get("title", "").strip()
            snippet = item.get("snippet", "")

            if not title or not link:
                continue

            emails = list(set(EMAIL_REGEX.findall(snippet)))

            results.append({
                "name": title,
                "website": link,
                "phone": "",
                "emails": emails,
                "address": "",
                "rating": None,
                "user_ratings_total": 0,
                "types": ["web_search"],
                "business_status": "",
                "price_level": None,
                "source": "Custom Search",
                "snippet": snippet,
            })

        if start >= 91:
            break
        start += 10

    return results
