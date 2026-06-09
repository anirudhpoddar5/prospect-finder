import requests
import time
from typing import Optional


PLACES_API_BASE = "https://maps.googleapis.com/maps/api/place"

# Google's type filters that map to our business categories
TYPE_MAP = {
    "med spa": ["spa", "health", "beauty_salon"],
    "medical spa": ["spa", "health", "beauty_salon"],
    "medspa": ["spa", "health", "beauty_salon"],
    "aesthetics": ["beauty_salon", "health"],
    "aesthetic clinic": ["health", "doctor"],
    "skin clinic": ["health", "beauty_salon"],
    "cosmetic dentist": ["dentist", "health"],
    "dental spa": ["dentist", "health"],
    "esthetic dentistry": ["dentist", "health"],
    "cosmetic dental": ["dentist", "health"],
    "dermatologist": ["doctor", "health"],
    "acupuncture": ["health"],
}


def search_businesses(api_key: str, business_type: str, location: str, max_results: int = 60):
    """
    Search Google Places for businesses matching type + location.
    Returns list of dicts with place_id, name, address, rating, business_status.
    Handles pagination up to max_results.
    """
    seen_place_ids = set()
    all_results = []
    next_page_token = None

    # First query: textSearch
    query = f"{business_type} in {location}"
    url = f"{PLACES_API_BASE}/textsearch/json"
    params = {
        "query": query,
        "key": api_key,
    }

    # Add type filter if we have one
    type_key = business_type.lower().strip()
    if type_key in TYPE_MAP:
        params["type"] = "|".join(TYPE_MAP[type_key])

    page = 0
    while len(all_results) < max_results:
        page += 1
        if next_page_token:
            params["pagetoken"] = next_page_token
            # Google requires a short delay before using pagetoken
            time.sleep(2)

        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
        except Exception as e:
            yield {"type": "error", "message": f"Google Places API error: {e}"}
            break

        if data.get("status") != "OK" and data.get("status") != "ZERO_RESULTS":
            error_msg = data.get("error_message", data.get("status", "Unknown error"))
            yield {"type": "error", "message": f"Google Places API: {error_msg}"}
            break

        results = data.get("results", [])
        if not results:
            break

        for place in results:
            place_id = place.get("place_id")
            if not place_id or place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)

            # Filter out permanently closed
            if place.get("business_status") == "CLOSED_PERMANENTLY":
                continue

            all_results.append({
                "place_id": place_id,
                "name": place.get("name", ""),
                "address": place.get("formatted_address", ""),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "business_status": place.get("business_status", "UNKNOWN"),
                "types": place.get("types", []),
                "price_level": place.get("price_level"),
            })

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

        yield {
            "type": "progress",
            "message": f"Page {page}: {len(all_results)} businesses found so far",
            "count": len(all_results),
        }

    yield {
        "type": "progress",
        "message": f"Discovery complete: {len(all_results)} businesses",
        "count": len(all_results),
    }

    # Now get detailed info for each
    details_url = f"{PLACES_API_BASE}/details/json"
    enriched = []
    for i, biz in enumerate(all_results):
        try:
            detail_params = {
                "place_id": biz["place_id"],
                "fields": "name,formatted_phone_number,website,opening_hours,editorial_summary",
                "key": api_key,
            }
            resp = requests.get(details_url, params=detail_params, timeout=10)
            detail_data = resp.json()
        except Exception:
            enriched.append(biz)
            continue

        if detail_data.get("status") == "OK":
            result = detail_data.get("result", {})
            biz["phone"] = result.get("formatted_phone_number", "")
            biz["website"] = result.get("website", "")
            biz["opening_hours"] = result.get("opening_hours", {})
            biz["summary"] = result.get("editorial_summary", {}).get("overview", "")

        enriched.append(biz)

        if (i + 1) % 10 == 0:
            yield {
                "type": "details",
                "message": f"Fetched details: {i + 1}/{len(all_results)}",
                "count": len(enriched),
            }

    yield {
        "type": "complete",
        "results": enriched,
        "count": len(enriched),
    }
