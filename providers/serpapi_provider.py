"""
SerpAPI Provider - Discovery + Enrichment via Google search results.
Free tier: 50 requests/hour (~1 per 72s).
"""
import requests
import re
import time
from urllib.parse import urlparse

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
LINKEDIN_REGEX = re.compile(r"linkedin\.com/(?:in|company)/[\w-]+")
INSTAGRAM_REGEX = re.compile(r"(?:instagram\.com/|@)([\w.]+)")
FACEBOOK_REGEX = re.compile(r"facebook\.com/[\w.]+")

BLOCKED_EMAIL_PATTERNS = [
    r"noreply@", r"no-reply@", r"donotreply@", r"example@",
    r"test@", r"email@email\.com", r"user@", r"admin@localhost",
    r"@domain\.com", r"@yourdomain\.com", r"@yoursite\.com",
    r"@example\.com", r"@test\.com", r"@sentry\.com",
    r"@google\.com", r"@facebook\.com", r"@instagram\.com",
    r"info@example", r"contact@example",
]

def is_valid_email(email: str) -> bool:
    email_lower = email.lower()
    for pattern in BLOCKED_EMAIL_PATTERNS:
        if re.search(pattern, email_lower):
            return False
    parts = email_lower.split(".")
    if len(parts) < 2:
        return False
    tld = parts[-1]
    if len(tld) < 2 or len(tld) > 6:
        return False
    return True

# ─── Rate limiting (in-memory, per-process) ───────────────────────────────
_serpapi_last_call: float = 0.0
_MIN_INTERVAL = 75.0  # seconds between calls (free tier: 50/hr)

def _rate_limit():
    global _serpapi_last_call
    elapsed = time.time() - _serpapi_last_call
    if elapsed < _MIN_INTERVAL:
        sleep_for = _MIN_INTERVAL - elapsed
        time.sleep(sleep_for)
    _serpapi_last_call = time.time()


def search_serpapi(api_key: str, business_type: str, city: str, state: str = "", country: str = "US", max_results: int = 10) -> list[dict]:
    if not api_key:
        return []

    _rate_limit()

    results = []
    query = f"{business_type} {city}"
    if state:
        query += f" {state}"
    if country and country.upper() != "US":
        query += f" {country}"

    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "api_key": api_key,
        "num": min(max_results, 10),
        "hl": "en",
        "gl": "us" if country.upper() == "US" else country.lower(),
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    organic_results = data.get("organic_results", [])
    for r in organic_results:
        title = r.get("title", "")
        link = r.get("link", "")
        snippet = r.get("snippet", "")

        if not title or not link:
            continue

        domain = urlparse(link).netloc.replace("www.", "").lower()

        skip_domains = {"yelp.com", "yellowpages.com", "bbb.org", "manta.com",
                        "mapquest.com", "tripadvisor.com", "realself.com", "thumbtack.com",
                        "nextdoor.com", "alignable.com", "coldlytics.com",
                        "facebook.com", "instagram.com", "linkedin.com",
                        "twitter.com", "tiktok.com", "maps.google.com"}

        if any(d in domain for d in skip_domains):
            continue

        _emails = []
        for e in EMAIL_REGEX.findall(snippet + " " + link):
            if is_valid_email(e) and e not in _emails:
                _emails.append(e)

        phones = []
        for p in PHONE_REGEX.findall(snippet):
            p_clean = p.strip()
            if p_clean not in phones:
                phones.append(p_clean)

        linkedin = ""
        instagram = ""
        facebook = ""

        if "linkedin.com" in link:
            linkedin = link if link.startswith("http") else "https://" + link
        elif "instagram.com" in link:
            instagram = link if link.startswith("http") else "https://" + link
        elif "facebook.com" in link:
            facebook = link if link.startswith("http") else "https://" + link

        results.append({
            "name": title[:100],
            "website": link,
            "phone": phones[0] if phones else "",
            "emails": _emails[:3],
            "address": "",
            "rating": None,
            "user_ratings_total": 0,
            "types": [business_type],
            "business_status": "",
            "price_level": None,
            "linkedin": linkedin,
            "instagram": instagram,
            "facebook": facebook,
            "source": "SerpAPI",
        })

        if len(results) >= max_results:
            break

    return results


def enrich_serpapi(api_key: str, biz_name: str, city: str, state: str, country: str, website: str = "") -> dict:
    if not api_key:
        return {"emails": [], "phones": [], "linkedin": "", "instagram": "", "facebook": ""}

    _rate_limit()

    result = {"emails": [], "phones": [], "linkedin": "", "instagram": "", "facebook": ""}

    queries = [
        f'"{biz_name}" {city} email OR contact OR "info@"',
        f'"{biz_name}" {city} linkedin facebook instagram',
    ]
    if website:
        domain = urlparse(website).netloc.replace("www.", "").lower()
        if domain:
            queries.append(f'site:{domain} email OR contact OR "info@"')

    seen_snippets = set()

    for query in queries:
        params = {
            "q": query,
            "api_key": api_key,
            "num": 5,
            "hl": "en",
            "gl": "us" if country.upper() == "US" else country.lower(),
        }
        try:
            resp = requests.get("https://serpapi.com/search.json", params=params, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception:
            continue

        organic_results = data.get("organic_results", [])
        for r in organic_results:
            snippet = (r.get("title", "") + " " + r.get("snippet", "")).strip()
            url = r.get("link", "")

            snippet_key = snippet[:100]
            if snippet_key in seen_snippets:
                continue
            seen_snippets.add(snippet_key)

            found_emails = EMAIL_REGEX.findall(snippet + " " + url)
            for e in found_emails:
                if is_valid_email(e) and e not in result["emails"]:
                    result["emails"].append(e)

            found_phones = PHONE_REGEX.findall(snippet)
            for p in found_phones:
                p_clean = p.strip()
                if p_clean not in result["phones"]:
                    result["phones"].append(p_clean)

            li_match = LINKEDIN_REGEX.search(snippet + " " + url)
            if li_match and not result["linkedin"]:
                result["linkedin"] = "https://www." + li_match.group(0)

            ig_match = INSTAGRAM_REGEX.search(snippet + " " + url)
            if ig_match and not result["instagram"]:
                username = ig_match.group(1)
                if username and len(username) > 2:
                    result["instagram"] = f"https://instagram.com/{username}"

            fb_match = FACEBOOK_REGEX.search(url)
            if fb_match and not result["facebook"]:
                result["facebook"] = "https://www." + fb_match.group(0)

    result["emails"] = result["emails"][:5]
    result["phones"] = result["phones"][:3]
    return result
