import requests
from typing import Generator, Optional

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
    "gym": "leisure.fitness",
    "restaurant": "catering.restaurant",
    "cafe": "catering.cafe",
    "bakery": "catering.bakery",
    "hotel": "accommodation.hotel",
    "tattoo": "commercial.beauty.tattoo_parlor",
    "barber": "commercial.beauty.barber",
    "nail salon": "commercial.beauty.nail_salon",
    "physio": "healthcare.physiotherapist",
    "chiropractor": "healthcare.chiropractor",
    "optician": "healthcare.optometrist",
    "pharmacy": "healthcare.pharmacy",
    "vet": "healthcare.veterinary",
    "auto repair": "service.vehicle.workshop",
    "plumber": "service.maintenance.plumber",
    "electrician": "service.maintenance.electrician",
    "cleaner": "service.maintenance.cleaning",
    "laundry": "service.maintenance.laundry",
    "dry cleaner": "service.maintenance.dry_cleaning",
    "accountant": "service.financial.accountant",
    "lawyer": "service.legal.lawyer",
    "real estate": "service.business_services.real_estate",
    "travel agent": "leisure.travel.travel_agency",
}


def _geoapify_categories(business_type: str) -> Optional[str]:
    bt = business_type.lower().strip()
    for key, val in CATEGORY_MAP.items():
        if key in bt:
            return val
    return None


def _fetch_places(api_key: str, categories: str, lat: float, lon: float) -> list:
    try:
        resp = requests.get(PLACES_URL, params={
            "apiKey": api_key,
            "categories": categories,
            "filter": f"circle:{lon},{lat},10000",
            "limit": 20,
            "lang": "en",
        }, timeout=15)
        if resp.status_code != 200:
            return []
        features = resp.json().get("features", [])
        results = []
        for f in features:
            p = f.get("properties", {})
            name = p.get("name", "").strip()
            if not name:
                continue
            contact = p.get("contact", {}) or {}
            cats = p.get("categories", [])
            if "private_household" in str(cats):
                continue
            results.append({
                "name": name,
                "phone": contact.get("phone", "") or "",
                "website": contact.get("website", "") or "",
                "emails": [contact.get("email", "")] if contact.get("email") else [],
                "address": p.get("formatted", "") or "",
                "rating": p.get("rating"),
                "user_ratings_total": p.get("reviews", 0),
                "types": cats,
                "business_status": "",
                "price_level": None,
            })
        return results
    except Exception:
        return []


def search_geoapify(api_key: str, business_type: str, location: str) -> Generator[dict, None, None]:
    api_key = api_key.strip()
    if not api_key:
        yield {"type": "error", "message": "Geoapify API key not configured"}
        return

    categories = _geoapify_categories(business_type)
    if not categories:
        yield {"type": "complete", "results": []}
        return

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

    results = _fetch_places(api_key, categories, lat, lon)
    yield {"type": "complete", "results": results}
