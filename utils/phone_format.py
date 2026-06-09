import re
from typing import Optional


def format_phone(raw: str) -> str:
    """Clean and format phone number to a readable format."""
    digits = re.sub(r'\D', '', raw)

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    elif len(digits) >= 7:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:11]}" if len(digits) > 7 else f"{digits[:3]}-{digits[3:]}"
    return raw


def digits_only(phone: str) -> str:
    """Extract only digits from phone string."""
    return re.sub(r'\D', '', phone)
