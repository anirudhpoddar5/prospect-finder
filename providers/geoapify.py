import requests
import time
from typing import Generator

GEOCODING_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"

CATEGORY_MAP = {
    "med spa": "commercial.beauty,healthcare.beauty",
    "medical spa": "commercial.beauty,healthcare.beauty",
    "cosmetic dentist": "healthcare.dentist",
    "cosmetic dentistry": "healthcare.dentist",
    "dentist": "healthcare.dentist",
    "plastic surgeon": "healthcare.doctor.plastic_surgery",
    "dermatologist": "healthcare.doctor.dermatology",
    "spa": "commercial.beauty,leisure.spa",
    "beauty salon": "commercial.beauty",
    "hair salon": "commercial.beauty.hairdresser",
}


def _geoapify_categories(business_type: str) -> str:
    bt = business_type.lower().strip()
    for key, val in CATEGORY_MAP.items():
        if key in bt:
            return val
    return f"commercial.{bt.replace(' ', '_')}"


def search_geoapify(api_key: str, business_type: str, location: str) -> Generator[dict, None, None]:
    api_key = api_key.strip()
    if not api_key:
        yield {"type": "error", "message": "Geoapify API key not configured"}
        return

    categories = _geoapify_categories(business_type)

    geo_resp = requests.get(
        GEOCODING_URL,
        params={"text": location, "apiKey": api_key, "limit": 1, "lang": "en"},
        timeout=10,
    )
    if geo_resp.status_code != 200:
        yield {"type": "error", "message": f"Geocoding failed: {geo_resp.status_code}"}
        return

    geo_data = geo_resp.json()
    features = geo_data.get("features", [])
    if not features:
        yield {"type": "error", "message": f"Could not geocode location: {location}"}
        return

    props = features[0]["properties"]
    lat, lon = props["lat"], props["lon"]

    params = {
        "apiKey": api_key,
        "categories": categories,
        "filter": f"circle:{lon},{lat},10000",
        "limit": 20,
        "lang": "en",
    }

    try:
        resp = requests.get(PLACES_URL, params=params, timeout=15)
        if resp.status_code != 200:
            yield {"type": "error", "message": f"Geoapify Places error: {resp.status_code}"}
            return

        data = resp.json()
        features = data.get("features", [])

        results = []
        for f in features:
            p = f.get("properties", {})
            name = p.get("name", "").strip()
            if not name:
                continue

            contact = p.get("contact", {}) or {}
            address = p.get("formatted", "")
            phone = contact.get("phone", "")
            website = contact.get("website", "")
            email = contact.get("email", "")
            rating = p.get("rating")
            reviews = p.get("reviews", 0)
            cats = p.get("categories", [])

            if "private_household" in str(cats):
                continue

            results.append({
                "name": name,
                "phone": phone or "",
                "website": website or "",
                "emails": [email] if email else [],
                "address": address or "",
                "rating": rating,
                "user_ratings_total": reviews,
                "types": cats,
                "business_status": "",
                "price_level": None,
            })

        yield {"type": "complete", "results": results}

    except Exception as e:
        yield {"type": "error", "message": f"Geoapify request failed: {e}"}
