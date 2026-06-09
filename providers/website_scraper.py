import re
import time
import requests

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

PHONE_REGEX = re.compile(
    r"(?:\(\d{3}\)[-.\s]\d{3}[-.\s]\d{4})"           # (xxx) xxx-xxxx
    r"|(?:\+\d{1,3}[-.\s]\d{3}[-.\s]\d{3}[-.\s]\d{4})"  # +xx xxx xxx xxxx
    r"|(?:\d{3}[-.\s]\d{3}[-.\s]\d{4})"                  # xxx-xxx-xxxx
)

OBSF_EMAIL = re.compile(
    r"\b([a-zA-Z0-9._%+-]+)\s*\[?at\]?\s*([a-zA-Z0-9.-]+)\s*\[?dot\]?\s*([a-zA-Z]{2,})\b",
    re.I,
)

MAILTO_REGEX = re.compile(r'href=["\']mailto:([^"\']+)["\']', re.I)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

PAGE_PATHS = [
    "/contact", "/about", "/contact-us",
    "/team", "/staff", "/about-us",
    "/services", "/locations",
    "/get-in-touch", "/book-online",
    "/appointments", "/faq",
]

VALID_TLDS = {
    "com", "net", "org", "edu", "gov", "mil", "co", "io", "ai",
    "uk", "au", "sg", "in", "ca", "nz", "de", "fr", "es", "it",
    "nl", "se", "no", "dk", "fi", "jp", "cn", "kr", "br", "mx",
    "us", "eu", "info", "biz", "tv", "me", "pro", "name",
    "ch", "at", "be", "pl", "cz", "hu", "ro", "ru", "za",
}

BLOCKED = [
    "noreply@", "no-reply@", "donotreply@",
    "example@", "test@", "domain.com", "yoursite.com",
    "sentry@", "sentry.io", "wixpress.com", "wordpress.com",
    "info@example", "contact@example", "email@email.com",
    "@example.com", "@domain.com", "@yoursite.com",
]


def _blocked(email: str) -> bool:
    el = email.lower()
    if any(b in el for b in BLOCKED):
        return True
    parts = el.split(".")
    if len(parts) < 2:
        return True
    tld = parts[-1]
    return len(tld) < 2 or len(tld) > 6 or tld not in VALID_TLDS


def _parse_obfuscated(text: str) -> list[str]:
    found = []
    for m in OBSF_EMAIL.finditer(text):
        local, domain, tld = m.groups()
        email = f"{local.lower()}@{domain.lower()}.{tld.lower()}"
        email = re.sub(r"\s+", "", email)
        if not _blocked(email) and EMAIL_REGEX.match(email):
            found.append(email)
    return found


def _valid_phone(p: str) -> bool:
    digits = re.sub(r"\D", "", p)
    if len(digits) < 10 or len(digits) > 11:
        return False
    if len(set(digits)) < 4:
        return False
    if digits in ("0000000000", "1234567890", "1111111111", "2222222222",
                  "3333333333", "4444444444", "5555555555", "6666666666",
                  "7777777777", "8888888888", "9999999999"):
        return False
    if not p.startswith("(") and not p.startswith("+") and not p.startswith("1"):
        if digits[0] in ("0", "1"):
            return False
    return True


def _scrape_url(url: str, emails: list, phones: list, deadline: float):
    if time.time() >= deadline:
        return
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(3, 4))
        if resp.status_code != 200:
            return
        text = resp.text
        em_lower = [e.lower() for e in emails]

        for e in EMAIL_REGEX.findall(text):
            e = e.replace("%20", "").strip()
            if e and not _blocked(e) and e.lower() not in em_lower:
                emails.append(e)
                em_lower.append(e.lower())

        for e in _parse_obfuscated(text):
            if e.lower() not in em_lower:
                emails.append(e)
                em_lower.append(e.lower())

        for m in MAILTO_REGEX.findall(text):
            m = m.strip().split("?")[0]
            m = m.replace("%20", "").strip()
            if not _blocked(m) and m.lower() not in em_lower and EMAIL_REGEX.match(m):
                emails.append(m)
                em_lower.append(m.lower())

        for p in PHONE_REGEX.findall(text):
            p_clean = p.strip()
            if p_clean not in phones and _valid_phone(p_clean):
                phones.append(p_clean)

    except Exception:
        pass


def scrape_website(website_url: str, timeout: int = 8):
    result = {"emails": [], "phones": []}

    if not website_url:
        return result

    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    base = website_url.rstrip("/")
    deadline = time.time() + timeout

    _scrape_url(base, result["emails"], result["phones"], deadline)

    for path in PAGE_PATHS:
        if len(result["emails"]) >= 3 or time.time() >= deadline:
            break
        _scrape_url(base + path, result["emails"], result["phones"], deadline)

    return result
