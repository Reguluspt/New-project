from __future__ import annotations

from typing import Any, Mapping


DEFAULT_PROFESSIONAL_RECIPIENT = "Kietna@cenvalue.vn"
PROFESSIONAL_RECIPIENT_OPTIONS = {
    "kiet": DEFAULT_PROFESSIONAL_RECIPIENT,
    "anhvu": "anhvtn6@cenvalue.vn",
    "truongpnt": "truongpnt@cenvalue.vn",
}


def professional_recipient_greeting(value: object) -> str:
    recipient = normalize_professional_recipient(value)
    if recipient.casefold() == PROFESSIONAL_RECIPIENT_OPTIONS["anhvu"].casefold():
        return "Chị Ánh"
    if recipient.casefold() == PROFESSIONAL_RECIPIENT_OPTIONS["truongpnt"].casefold():
        return "Truong"
    return "Kiệt"


def professional_forward_enabled(record: Mapping[str, Any]) -> bool:
    value = str(record.get("professional_forward_enabled") or "1").strip().casefold()
    return value not in {"0", "false", "no", "off", "khong", "không"}


def normalize_professional_recipient(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return DEFAULT_PROFESSIONAL_RECIPIENT
    for option in PROFESSIONAL_RECIPIENT_OPTIONS.values():
        if raw.casefold() == option.casefold():
            return option
    return raw


def professional_recipient_from_record(record: Mapping[str, Any], fallback: str = "") -> str:
    return normalize_professional_recipient(
        record.get("professional_recipient_email") or fallback or DEFAULT_PROFESSIONAL_RECIPIENT
    )


def professional_choice_values(choice: str) -> dict[str, str]:
    if choice == "none":
        return {
            "professional_forward_enabled": "0",
            "professional_recipient_email": "",
        }
    return {
        "professional_forward_enabled": "1",
        "professional_recipient_email": PROFESSIONAL_RECIPIENT_OPTIONS.get(choice, DEFAULT_PROFESSIONAL_RECIPIENT),
    }
