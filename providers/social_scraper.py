import re
import requests
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


def scrape_facebook_page(url: str, timeout: int = 10):
    """
    Scrape a public Facebook page's About section for email and contact info.
    Uses m.facebook.com (mobile site, easier to parse).
    Returns dict with emails and phones found.
    """
    result = {"emails": [], "phones": []}

    # Normalize URL to mobile version
    fb_url = url.replace("www.facebook.com", "m.facebook.com")
    if "/about" not in fb_url:
        fb_url = fb_url.rstrip("/") + "/about"

    try:
        resp = requests.get(fb_url, headers=HEADERS, timeout=(3, timeout))
        if resp.status_code != 200:
            return result

        text = resp.text

        # Try to find email in the page text
        found_emails = EMAIL_REGEX.findall(text)
        for e in found_emails:
            e_lower = e.lower()
            if (e_lower not in [r.lower() for r in result["emails"]] and
                not any(block in e_lower for block in
                        ["noreply@", "no-reply@", "example@", "test@"])):
                result["emails"].append(e)

        found_phones = PHONE_REGEX.findall(text)
        for p in found_phones:
            p_clean = p.strip()
            if p_clean not in result["phones"]:
                result["phones"].append(p_clean)

    except Exception:
        pass

    return result


def scrape_instagram_bio(url: str, timeout: int = 10):
    """
    Scrape an Instagram profile's bio for email and contact info.
    Parses the public profile page HTML.
    Returns dict with emails found.
    """
    result = {"emails": [], "phones": []}

    # Normalize URL
    ig_url = url.rstrip("/")
    if "?" in ig_url:
        ig_url = ig_url.split("?")[0]

    try:
        resp = requests.get(ig_url, headers=HEADERS, timeout=(3, timeout))
        if resp.status_code != 200:
            return result

        text = resp.text

        # Extract bio text from meta description or JSON embedded in page
        # Instagram puts bio info in meta tags and script tags

        # Method 1: Meta description tag
        meta_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', text)
        if meta_match:
            bio_text = meta_match.group(1)
            found_emails = EMAIL_REGEX.findall(bio_text)
            for e in found_emails:
                e_lower = e.lower()
                if e_lower not in [r.lower() for r in result["emails"]]:
                    result["emails"].append(e)

        # Method 2: JSON-LD structured data
        json_match = re.search(r'<script type="application/ld\+json">([^<]+)</script>', text)
        if json_match:
            json_text = json_match.group(1)
            found_emails = EMAIL_REGEX.findall(json_text)
            for e in found_emails:
                e_lower = e.lower()
                if e_lower not in [r.lower() for r in result["emails"]]:
                    result["emails"].append(e)

        # Method 3: Window._sharedData (if available)
        shared_match = re.search(r'window\._sharedData\s*=\s*({.+?});', text)
        if shared_match:
            import json
            try:
                shared_data = json.loads(shared_match.group(1))
                # Navigate to find biography
                entry = (shared_data.get("entry_data", {})
                         .get("ProfilePage", [{}])[0]
                         .get("graphql", {})
                         .get("user", {})
                         .get("biography", ""))
                if entry:
                    found_emails = EMAIL_REGEX.findall(entry)
                    for e in found_emails:
                        e_lower = e.lower()
                        if e_lower not in [r.lower() for r in result["emails"]]:
                            result["emails"].append(e)

                    found_phones = PHONE_REGEX.findall(entry)
                    for p in found_phones:
                        p_clean = p.strip()
                        if p_clean not in result["phones"]:
                            result["phones"].append(p_clean)
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

    except Exception:
        pass

    return result
