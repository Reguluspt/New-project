from __future__ import annotations

import re


SHORT_CONTRACT_PATTERN = re.compile(r"\b([A-Z]\d{2})([-./])(\d{4})\b", re.IGNORECASE)


def short_contract_number(contract_number: object, *, fallback: str = "") -> str:
    text = str(contract_number or "").strip()
    if not text:
        return fallback
    match = SHORT_CONTRACT_PATTERN.search(text)
    if not match:
        return text
    return f"{match.group(1).upper()}{match.group(2)}{match.group(3)}"
