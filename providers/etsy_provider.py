import re
import requests
from bs4 import BeautifulSoup
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def search_etsy(query: str, max_results: int = 20) -> list[dict]:
    results = []

    ddg_url = "https://html.duckduckgo.com/html/"
    params = {"q": f"site:etsy.com {query}"}

    try:
        resp = requests.get(ddg_url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return results
    except Exception:
        return results

    soup = BeautifulSoup(resp.text, "html.parser")

    for i, link in enumerate(soup.select(".result__a")):
        if len(results) >= max_results:
            break

        href = link.get("href")
        if not href:
            continue

        ddg_redirect = _extract_ddg_url(href)
        if not ddg_redirect or "/listing/" not in ddg_redirect:
            continue

        title = link.get_text(strip=True)

        snippet_el = link.find_parent(".result") or link.find_parent("div")
        snippet = ""
        if snippet_el:
            sn = snippet_el.select_one(".result__snippet")
            if sn:
                snippet = sn.get_text(strip=True)

        shop_name = _extract_shop_name(title, ddg_redirect)
        if not shop_name:
            continue

        results.append({
            "name": shop_name,
            "website": ddg_redirect,
            "phone": "",
            "emails": [],
            "address": "",
            "rating": None,
            "user_ratings_total": 0,
            "types": ["etsy_shop"],
            "business_status": "",
            "price_level": None,
            "source": "Etsy",
        })

    return results


def _extract_ddg_url(redirect_url: str) -> Optional[str]:
    match = re.search(r"uddg=([^&]+)", redirect_url)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    return redirect_url if redirect_url.startswith("http") else None


def _extract_shop_name(title: str, url: str) -> Optional[str]:
    shop_match = re.search(r"/shop/([^/?#]+)", url)
    if shop_match:
        name = shop_match.group(1).replace("-", " ").replace("_", " ").title()
        return name

    name_match = re.search(r"by\s+(\w[\w\s]{1,30}\w)\s*\|", title)
    if name_match:
        return name_match.group(1).strip()

    dash_idx = title.rfind(" - ")
    if dash_idx > 0:
        return title[:dash_idx].strip()

    return None
