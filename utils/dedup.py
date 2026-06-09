import csv
import re
import os
from typing import List, Tuple, Optional

try:
    from Levenshtein import ratio as lev_ratio
except ImportError:
    def lev_ratio(a, b):
        """Fallback: simple character overlap ratio."""
        if not a or not b:
            return 0.0
        a, b = a.lower(), b.lower()
        if a == b:
            return 1.0
        intersection = len(set(a) & set(b))
        return intersection / max(len(set(a)), len(set(b)), 1)


def normalize_name(name: str) -> str:
    """Normalize business name for comparison."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    # Remove common business suffixes
    suffixes = [' llc', ' inc', ' corp', ' pllc', ' pa', ' ltd', ' pvt']
    for s in suffixes:
        if name.endswith(s):
            name = name[:-len(s)]
    return name.strip()


def normalize_phone(phone: str) -> str:
    """Strip phone to digits for comparison."""
    return re.sub(r'\D', '', phone)


def normalize_city(city: str) -> str:
    """Normalize city name."""
    return city.lower().strip().replace(" ", "")


def load_existing_prospects(csv_path: str) -> List[dict]:
    """Load existing CSV and return normalized records for dedup."""
    records = []
    if not os.path.exists(csv_path):
        return records

    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("CLINIC NAME") or row.get("name") or row.get("Name") or "").strip()
                city = (row.get("CITY") or row.get("city") or row.get("City") or "").strip()
                state = (row.get("STATE") or row.get("state") or row.get("State") or "").strip()
                phone = (row.get("PHONE") or row.get("phone") or row.get("Phone") or "").strip()
                email = (row.get("EMAIL") or row.get("email") or row.get("Email") or "").strip()

                if name:
                    records.append({
                        "name": name,
                        "name_norm": normalize_name(name),
                        "city": normalize_city(city),
                        "state": state.lower().strip(),
                        "phone": normalize_phone(phone),
                        "email": email.lower().strip(),
                    })
    except Exception:
        pass

    return records


def is_duplicate(new_biz: dict, existing: List[dict], threshold: float = 0.75) -> Tuple[bool, str]:
    """
    Check if a business already exists in the existing list.
    Uses fuzzy name matching + city/phone for verification.
    Returns (is_duplicate, reason).
    """
    new_name = normalize_name(new_biz.get("name", ""))
    new_city = normalize_city(new_biz.get("city", ""))
    new_phone = normalize_phone(new_biz.get("phone", ""))

    if not new_name:
        return False, ""

    for ex in existing:
        # Exact phone match → duplicate
        if new_phone and ex["phone"] and new_phone == ex["phone"]:
            return True, f"Same phone as '{ex['name']}'"

        # Same city + similar name
        if new_city and ex["city"] and new_city == ex["city"]:
            similarity = lev_ratio(new_name, ex["name_norm"])
            if similarity >= threshold:
                return True, f"Fuzzy name match ({similarity:.0%}) with '{ex['name']}'"

            # Same phone in new vs existing (partial match)
            if new_phone and ex["phone"] and new_phone[-4:] == ex["phone"][-4:]:
                if similarity >= 0.5:
                    return True, f"Partial phone + name match ({similarity:.0%}) with '{ex['name']}'"

    return False, ""
