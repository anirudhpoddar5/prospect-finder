import re
import time
from typing import Optional

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
LINKEDIN_REGEX = re.compile(r"linkedin\.com/(?:in|company)/[\w-]+")
INSTAGRAM_REGEX = re.compile(r"(?:instagram\.com/|@)([\w.]+)")
FACEBOOK_REGEX = re.compile(r"facebook\.com/[\w.]+")

# Emails to exclude (non-contract)
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
    # Must have a real TLD
    parts = email_lower.split(".")
    if len(parts) < 2:
        return False
    tld = parts[-1]
    if len(tld) < 2 or len(tld) > 6:
        return False
    return True


def search_business(business_name: str, city: str, state: str, country: str = "US"):
    """
    Search DuckDuckGo for contact info of a specific business.
    Returns dict with emails, phones, linkedin, instagram, facebook, website.
    """
    result = {
        "emails": [],
        "phones": [],
        "linkedin": "",
        "instagram": "",
        "facebook": "",
        "website": "",
    }

    queries = [
        f'"{business_name}" {city} email contact info',
        f'"{business_name}" {city} linkedin facebook instagram',
    ]

    seen_snippets = set()

    with DDGS(timeout=10) as ddgs:
        for query in queries:
            try:
                search_results = list(ddgs.text(query, max_results=5, region=get_region(country)))
            except Exception:
                try:
                    search_results = list(ddgs.text(query, max_results=5))
                except Exception:
                    time.sleep(2)
                    try:
                        search_results = list(ddgs.text(query, max_results=5))
                    except Exception:
                        continue
            time.sleep(1.2)

            for r in search_results:
                snippet = (r.get("title", "") + " " + r.get("body", "")).strip()
                url = r.get("href", "")

                snippet_key = snippet[:100]
                if snippet_key in seen_snippets:
                    continue
                seen_snippets.add(snippet_key)

                # Extract emails
                found_emails = EMAIL_REGEX.findall(snippet + " " + url)
                for e in found_emails:
                    if is_valid_email(e) and e not in result["emails"]:
                        result["emails"].append(e)

                # Extract phone
                found_phones = PHONE_REGEX.findall(snippet)
                for p in found_phones:
                    p_clean = p.strip()
                    if p_clean not in result["phones"]:
                        result["phones"].append(p_clean)

                # Extract social + website
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

                # Extract secondary website (not from places API, from search)
                # Only if it looks like a real business website
                parsed_url = url.lower()
                if (url and not result["website"] and
                    not any(d in parsed_url for d in [
                        "facebook.com", "instagram.com", "linkedin.com",
                        "twitter.com", "yelp.com", "yellowpages",
                        "bbb.org", "realself.com", "thumbtack.com",
                        "nextdoor.com", "alignable.com",
                    ]) and
                    "google.com/maps" not in parsed_url and
                    len(url) > 10 and
                    "." in parsed_url):
                    result["website"] = url

    # Deduplicate and limit
    result["emails"] = result["emails"][:5]
    result["phones"] = result["phones"][:3]

    return result


def get_region(country: str) -> str:
    mapping = {
        "US": "us-en",
        "UK": "uk-en",
        "GB": "uk-en",
        "AU": "au-en",
        "SG": "sg-en",
        "IN": "in-en",
        "CA": "ca-en",
    }
    return mapping.get(country.upper(), "wt-wt")
