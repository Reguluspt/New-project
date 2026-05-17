from __future__ import annotations

import re
import datetime

SHORT_CONTRACT_PATTERN = re.compile(r"\b([A-Z]\d{2})([-./]?)(\d{4})\b", re.IGNORECASE)


def short_contract_number(contract_number: object, *, fallback: str = "") -> str:
    text = str(contract_number or "").strip()
    if not text:
        return fallback
    match = SHORT_CONTRACT_PATTERN.search(text)
    if not match:
        return text
    # Giữ nguyên dấu phân cách nếu có (dấu chấm hoặc dấu gạch ngang), mặc định là dấu gạch ngang
    sep = match.group(2) if match.group(2) else "-"
    return f"{match.group(1).upper()}{sep}{match.group(3)}"


def expand_contract_number(contract_number: object) -> str:
    text = str(contract_number or "").strip()
    now = datetime.datetime.now()
    year = now.year
    month_prefix = f"N{now.month:02d}"
    
    if not text:
        return f"010/{year}/{month_prefix}-/DN"
        
    if "010/" in text and "/DN" in text:
        return text
        
    # If the user typed .0833
    if text.startswith("."):
        num_part = text.lstrip(".")
        if num_part.isdigit():
            return f"010/{year}/{month_prefix}.{num_part}/DN"

    # Handle formats like N05-0833 or N05.0833
    if re.match(r"^[A-Z]\d{2}[-.]\d+$", text, re.IGNORECASE):
        return f"010/{year}/{text.upper()}/DN"
        
    # If the user typed just the numbers e.g. 0833
    if re.match(r"^\d+$", text):
        return f"010/{year}/{month_prefix}-{text}/DN"
        
    # fallback
    return f"010/{year}/{month_prefix}-{text}/DN"
