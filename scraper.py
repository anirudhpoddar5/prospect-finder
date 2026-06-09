import time
import re
import threading
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

from dataclasses import dataclass, field

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from providers.google_places import search_businesses
from providers.duckduckgo_provider import search_business, is_valid_email, guess_emails_from_domain
from providers.social_scraper import scrape_facebook_page, scrape_instagram_bio
from providers.website_scraper import scrape_website
from providers.geoapify import search_geoapify
from utils.dedup import load_existing_prospects, is_duplicate

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Thread-safe stop signal shared across worker threads
_scan_stop_event = threading.Event()

# Domains to exclude from discovery results
SKIP_DOMAINS = {
    "yelp.com", "yellowpages", "bbb.org", "manta.com",
    "mapquest", "tripadvisor", "realself.com", "thumbtack.com",
    "nextdoor.com", "alignable.com", "coldlytics.com",
    "allevents.in", "bing.com/aclick",
    "cell.com", "sciencedirect.com", "pubmed.ncbi.",
    "merriam-webster.com", "medlineplus.gov", "wikipedia",
    ".gov", ".edu", "amazon.com", "webmd.com",
    "healthline.com", "mayoclinic.org", "verywellhealth.com",
    "cnn.com", "bbc.", "news.google", "foxnews",
    "nytimes.com", "wsj.com", "reuters.com", "bloomberg.com",
    "news.yahoo", "msn.com", "medscape.com",
    "facebook.com", "instagram.com", "linkedin.com",
    "twitter.com", "tiktok.com",
}

SKIP_TITLE_WORDS = {"review", "jobs", "careers", "hiring", "for sale",
                     "top 10", "best 10", "near me", "things to do in"}
GENERIC_NAMES = {"advanced", "boutique", "services", "home", "contact",
                 "about", "specials", "gallery", "locations", "location",
                 "photos", "videos", "reviews", "portfolio", "blog",
                 "appointments", "book now", "book online", "specials",
                 "our locations", "our team", "our services"}


@dataclass
class ScanState:
    step: str = "init"
    biz_type_idx: int = 0
    loc_idx: int = 0
    biz_idx: int = 0
    all_results: list = field(default_factory=list)
    discovered: list = field(default_factory=list)
    existing: list = field(default_factory=list)
    per_city_stats: dict = field(default_factory=dict)
    total_email: int = 0
    total_phone: int = 0
    total_no_website: int = 0
    total_linkedin: int = 0
    total_new: int = 0
    total_hot: int = 0
    total_deduped: int = 0
    total_skipped_contact: int = 0
    business_types: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    api_key: str = ""
    geoapify_key: str = ""
    use_duckduckgo_only: bool = False
    max_leads: int = 0
    message: str = ""


def init_scan_state(api_key, business_types, locations, existing_csv_path,
                    use_duckduckgo_only, max_leads, geoapify_key="") -> ScanState:
    state = ScanState(
        api_key=api_key,
        geoapify_key=geoapify_key,
        business_types=business_types,
        locations=locations,
        use_duckduckgo_only=use_duckduckgo_only,
        max_leads=max_leads,
    )
    if existing_csv_path:
        state.existing = load_existing_prospects(existing_csv_path)
    return state


def run_scan_step(state: ScanState, stop_flag: callable = None) -> dict:
    if stop_flag and stop_flag():
        _scan_stop_event.set()
        state.step = "stopped"
        return _complete(state)

    if state.step == "init":
        state.step = "discover"
        state.message = f"Loaded {len(state.existing)} existing prospects for dedup" if state.existing else ""
        return {"type": "status", "message": state.message} if state.message else _next_phase(state)

    if state.step == "discover":
        return _discover_step(state)

    if state.step == "enrich":
        return _enrich_step(state, stop_flag)

    if state.step == "complete" or state.step == "stopped":
        return _complete(state)

    return {"type": "status", "message": "Unknown step"}


def _next_phase(state: ScanState) -> dict:
    biz_types = state.business_types
    locs = state.locations
    bt_idx = state.biz_type_idx
    l_idx = state.loc_idx

    if bt_idx >= len(biz_types):
        state.step = "complete"
        return _complete(state)

    if l_idx >= len(locs):
        state.biz_type_idx += 1
        state.loc_idx = 0
        return _next_phase(state)

    biz_type = biz_types[bt_idx]
    loc = locs[l_idx]
    city = loc.get("city", "")
    state_name = loc.get("state", "")
    country = loc.get("country", "US")

    total_tasks = len(biz_types) * len(locs)
    completed = bt_idx * len(locs) + l_idx
    task_label = f"{biz_type} in {city}, {state_name or country}"

    return {
        "type": "phase",
        "phase": 1,
        "message": f"[{completed + 1}/{total_tasks}] Discovering: {task_label}",
        "progress": completed / total_tasks,
    }


def _discover_step(state: ScanState) -> dict:
    biz_type = state.business_types[state.biz_type_idx]
    loc = state.locations[state.loc_idx]
    city = loc.get("city", "")
    state_name = loc.get("state", "")
    country = loc.get("country", "US")

    if state.geoapify_key:
        discovered = []
        for update in search_geoapify(state.geoapify_key, biz_type, f"{city} {state_name or country}"):
            if update["type"] == "complete":
                discovered = update["results"]
            elif update["type"] == "error":
                return update
        msg = f"Geoapify found {len(discovered)} businesses in {city}"
    elif state.use_duckduckgo_only:
        discovered = discover_via_duckduckgo(
            biz_type, city, state_name, country,
            max_leads=state.max_leads or 10,
        )
        msg = f"DuckDuckGo found {len(discovered)} potential businesses in {city}"
    else:
        discovered = []
        for update in search_businesses(state.api_key, biz_type, f"{city} {state_name or country}"):
            if update["type"] == "complete":
                discovered = update["results"]
            elif update["type"] == "error":
                return update
        msg = f"Google found {len(discovered)} businesses in {city}"

    if not discovered:
        state.loc_idx += 1
        return {"type": "status", "message": f"No results for {biz_type} in {city}, {state_name or country}"}

    state.discovered = (discovered[:state.max_leads] if state.max_leads else discovered)
    state.biz_idx = 0
    state.step = "enrich"

    return {"type": "status", "message": msg}


def _enrich_step(state: ScanState, stop_flag: callable = None) -> dict:
    biz_type = state.business_types[state.biz_type_idx]
    loc = state.locations[state.loc_idx]
    discovered = state.discovered

    if state.biz_idx >= len(discovered):
        city_key = f"{biz_type} in {loc['city']}, {loc.get('state') or loc.get('country')}"
        state.per_city_stats[city_key] = {
            "found": len(discovered),
            "new": state.total_new,
            "deduped": state.total_deduped,
            "skipped_no_contact": state.total_skipped_contact,
            "with_email": state.total_email,
            "with_phone": state.total_phone,
            "no_website": state.total_no_website,
            "with_linkedin": state.total_linkedin,
            "hot": state.total_hot,
        }
        state.loc_idx += 1
        state.step = "discover"
        return _next_phase(state)

    biz = discovered[state.biz_idx]
    enriched, reason = _enrich_one(biz, biz_type, loc["city"], loc.get("state", ""),
                                   loc.get("country", "US"), state.existing, stop_flag)
    state.biz_idx += 1

    if reason == "no_contact":
        state.total_skipped_contact += 1
        return {
            "type": "enrichment_progress",
            "message": f"⏭ Skipped {state.biz_idx}/{len(discovered)}: {biz.get('name', '')[:40]} (no contact)",
            "current": state.biz_idx, "total": len(discovered), "result": None,
        }

    if reason == "deduped":
        state.total_deduped += 1
        return {
            "type": "enrichment_progress",
            "message": f"⏭ Deduped {state.biz_idx}/{len(discovered)}: {biz.get('name', '')[:40]}",
            "current": state.biz_idx, "total": len(discovered), "result": None,
        }

    if reason == "stopped":
        state.step = "stopped"
        return _complete(state)

    state.all_results.append(enriched)
    if enriched["emails"]:
        state.total_email += 1
    if enriched["phone"]:
        state.total_phone += 1
    if not enriched["has_website"]:
        state.total_no_website += 1
    if enriched["linkedin"]:
        state.total_linkedin += 1
    if enriched["lead_priority"] == "Hot":
        state.total_hot += 1
    state.total_new += 1

    return {
        "type": "enrichment_progress",
        "message": f"Enriched {state.biz_idx}/{len(discovered)}: {enriched['name'][:40]}"
                   f"{' ✅' if enriched['emails'] else ''}",
        "current": state.biz_idx, "total": len(discovered),
        "result": enriched,
    }


def _enrich_one(biz, biz_type, city, state_name, country, existing, stop_flag=None):
    if _scan_stop_event.is_set():
        return None, "stopped"

    biz_name = biz.get("name", "")
    biz_phone = biz.get("phone", "")
    biz_website = biz.get("website", "")
    biz_emails = biz.get("emails", [])

    enriched = {
        "name": biz_name,
        "category": biz_type,
        "city": city, "state": state_name, "country": country,
        "phone": biz_phone, "website": biz_website,
        "rating": biz.get("rating"),
        "review_count": biz.get("user_ratings_total", 0),
        "address": biz.get("address", ""),
        "price_level": biz.get("price_level"),
        "business_status": biz.get("business_status", ""),
        "types": ", ".join(biz.get("types", [])) if biz.get("types") else "",
        "emails": biz_emails[:],
        "linkedin": "", "instagram": "", "facebook": "",
        "has_website": bool(biz_website),
        "lead_priority": "Cold",
        "email_source": "", "enrichment_notes": "",
    }

    has_any_contact = bool(biz_phone or biz_website or biz_emails)
    item_deadline = time.time() + 60

    ddg = search_business(biz_name, city, state_name, country, website=biz_website)
    for e in ddg["emails"]:
        if e not in enriched["emails"]:
            enriched["emails"].append(e)
    enriched["linkedin"] = ddg["linkedin"]
    enriched["instagram"] = ddg["instagram"]
    enriched["facebook"] = ddg["facebook"]

    if not enriched["website"] and ddg["website"]:
        enriched["website"] = ddg["website"]
        enriched["has_website"] = True

    has_any_contact = has_any_contact or bool(enriched["emails"] or enriched["linkedin"])
    has_any_contact = has_any_contact or bool(enriched["instagram"] or enriched["facebook"])

    if enriched["facebook"] and not enriched["emails"] and time.time() < item_deadline:
        fb_data = scrape_facebook_page(enriched["facebook"], timeout=5)
        for e in fb_data["emails"]:
            if e not in enriched["emails"]:
                enriched["emails"].append(e)
                enriched["email_source"] = "Facebook"

    if enriched["instagram"] and not enriched["emails"] and time.time() < item_deadline:
        ig_data = scrape_instagram_bio(enriched["instagram"], timeout=5)
        for e in ig_data["emails"]:
            if e not in enriched["emails"]:
                enriched["emails"].append(e)
                enriched["email_source"] = "Instagram"

    if enriched["website"] and time.time() < item_deadline:
        ws_data = scrape_website(enriched["website"], timeout=14)
        for e in ws_data["emails"]:
            if e not in enriched["emails"]:
                enriched["emails"].append(e)
                enriched["email_source"] = "Website"
        if not enriched["phone"] and ws_data["phones"]:
            enriched["phone"] = ws_data["phones"][0]

    if not enriched["emails"] and enriched["website"]:
        for guess in guess_emails_from_domain(enriched["website"]):
            if guess not in enriched["emails"]:
                enriched["emails"].append(guess)
                enriched["email_source"] = "Domain guess"
                break

    has_any_contact = has_any_contact or bool(enriched["emails"])
    if not has_any_contact:
        return enriched, "no_contact"

    if existing:
        dup, reason = is_duplicate(enriched, existing)
        if dup:
            return enriched, "deduped"

    if enriched["emails"] and not enriched["has_website"]:
        enriched["lead_priority"] = "Hot"
        enriched["enrichment_notes"] = "Email found, no website"
    elif enriched["emails"]:
        enriched["lead_priority"] = "Hot"
        enriched["enrichment_notes"] = "Email found"
    elif enriched["linkedin"] and not enriched["has_website"]:
        enriched["lead_priority"] = "Hot"
        enriched["enrichment_notes"] = "LinkedIn found, no website"
    elif not enriched["has_website"]:
        enriched["lead_priority"] = "Warm"
        enriched["enrichment_notes"] = "No website, needs social discovery"
    elif enriched["linkedin"]:
        enriched["lead_priority"] = "Warm"
        enriched["enrichment_notes"] = "LinkedIn found"
    else:
        enriched["lead_priority"] = "Warm"
        enriched["enrichment_notes"] = "Has phone / social"

    if enriched["emails"] and not enriched["email_source"]:
        enriched["email_source"] = "DuckDuckGo"

    return enriched, "ok"


def _complete(state: ScanState) -> dict:
    return {
        "type": "complete",
        "results": state.all_results,
        "stats": {
            "total_found": len(state.all_results),
            "with_email": state.total_email,
            "with_phone": state.total_phone,
            "no_website": state.total_no_website,
            "with_linkedin": state.total_linkedin,
            "hot": state.total_hot,
            "deduped": state.total_deduped,
            "skipped_no_contact": state.total_skipped_contact,
        },
        "per_city_stats": state.per_city_stats,
    }


def _extract_ddg_url(el) -> str:
    href = el.get("href", "")
    if "uddg=" in href:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        return unquote(qs.get("uddg", [""])[0])
    return href


# Global session for DDG HTML requests to persist cookies across calls
_ddg_session = None


def _get_ddg_session():
    global _ddg_session
    if _ddg_session is None:
        s = requests.Session()
        try:
            s.get("https://duckduckgo.com/", headers=_HEADERS, timeout=10)
        except Exception:
            pass
        _ddg_session = s
    return _ddg_session


def discover_via_duckduckgo(business_type: str, city: str, state: str, country: str = "US",
                            max_leads: int = 10) -> list:
    query = f"{business_type} {city} {state}"
    seen_names = set()
    seen_urls = set()
    discovered = []

    if _scan_stop_event.is_set():
        return []

    session = _get_ddg_session()

    for attempt in range(2):
        if _scan_stop_event.is_set():
            return discovered

        try:
            resp = session.get(
                "https://html.duckduckgo.com/html",
                params={"q": query},
                headers=_HEADERS,
                timeout=15,
            )
            if resp.status_code == 429 or resp.status_code == 403:
                if attempt == 0:
                    time.sleep(10)
                    session = _get_ddg_session()
                    continue
                return discovered

            if resp.status_code != 200:
                return discovered

            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.select(".result")
        except Exception:
            if attempt == 0:
                time.sleep(5)
                continue
            return discovered

        if not results:
            return discovered

        for r in results:
            if _scan_stop_event.is_set():
                return discovered

            title_el = r.select_one(".result__title a, .result__a")
            snippet_el = r.select_one(".result__snippet")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url = _extract_ddg_url(title_el)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            if not title or not url:
                continue

            url_lower = url.lower()

            if any(d in url_lower for d in SKIP_DOMAINS):
                continue

            if any(w in title.lower() for w in SKIP_TITLE_WORDS):
                continue

            name = title
            if " | " in name:
                parts = [p.strip() for p in name.split(" | ")]
                parts = [p for p in parts if len(p) > 2 and p.lower() not in ("home", "homepage", "contact")]
                if parts:
                    best = min(parts, key=len)
                    long = max(parts, key=len)
                    short_is_generic = bool(re.match(r"^[\w\s]+ (TX|AZ|CA|NY|FL|UK|AU|SG|IN)$", best, re.I))
                    name = long if short_is_generic else best
            for suffix in [" - Home", " | Home", " - Homepage", " | Homepage",
                           " - Homepage", " | Facebook", " - Facebook"]:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
                    break
            name = re.sub(r"^Home\s*[-|]\s*", "", name).strip()

            name = name.strip()
            if not name or len(name) < 3:
                continue

            skip_name_patterns = [
                r"^\w+\s*,\s*\w+$",
                r"^\w+\s+(TX|CA|NY|FL|UK|AU|SG|IN)$",
                r"^best\s+", r"^top\s+", r"^new\s+",
            ]
            if any(re.match(p, name, re.I) for p in skip_name_patterns):
                continue

            if name.lower().strip() in GENERIC_NAMES:
                continue

            skip_in_name = ["medscape", "medical news", "webmd", "healthline", ".gov", ".edu"]
            if any(k in name.lower() for k in skip_in_name):
                continue

            name_key = name.lower().strip()
            if name_key in seen_names:
                continue

            try:
                domain = urlparse(url).netloc.replace("www.", "")
                if domain and domain in seen_urls:
                    continue
                if domain:
                    seen_urls.add(domain)
            except Exception:
                pass

            phones = re.findall(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", snippet)
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", snippet)

            if max_leads and len(discovered) >= max_leads:
                break

            seen_names.add(name_key)
            discovered.append({
                "name": name,
                "phone": phones[0] if phones else "",
                "website": url,
                "emails": emails,
                "address": "",
                "rating": None,
                "user_ratings_total": 0,
                "url": url,
                "snippet": snippet[:200],
            })

        break

    return discovered
