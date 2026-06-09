import re
import requests
from urllib.parse import urljoin, urlparse
from typing import Optional

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

CONTACT_PATHS = ["/contact", "/about", "/contact-us"]


def scrape_website(website_url: str, timeout: int = 10):
    """
    Scrape a business website for contact info.
    Tries common contact/about page paths.
    Returns dict with emails and phones.
    """
    result = {"emails": [], "phones": []}

    if not website_url:
        return result

    # Ensure URL has scheme
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    base = website_url.rstrip("/")

    # First try the homepage
    _scrape_url(base, result, timeout)

    # Then try common contact paths
    for path in CONTACT_PATHS:
        url = base + path
        if len(result["emails"]) >= 3:
            break
        _scrape_url(url, result, timeout)

    return result


def _scrape_url(url: str, result: dict, timeout: int):
    """Scrape a single URL for contact info."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(3, timeout))
        if resp.status_code != 200:
            return
        text = resp.text

        found_emails = EMAIL_REGEX.findall(text)
        for e in found_emails:
            e_lower = e.lower()
            if (e_lower not in [r.lower() for r in result["emails"]] and
                not any(block in e_lower for block in
                        ["noreply@", "no-reply@", "example@",
                         "test@", "domain.com", "yoursite.com",
                         "sentry@", "sentry.io", "wixpress.com",
                         "wordpress.com"])):
                result["emails"].append(e)

        found_phones = PHONE_REGEX.findall(text)
        for p in found_phones:
            p_clean = p.strip()
            if p_clean not in result["phones"]:
                result["phones"].append(p_clean)

    except Exception:
        pass
