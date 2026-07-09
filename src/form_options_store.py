from __future__ import annotations

import json
from pathlib import Path

from src.app_config import DATA_DIR


CUSTOM_FORM_OPTIONS_PATH = DATA_DIR / "custom_form_options.json"

ALLOWED_OPTION_FIELDS = {
    "valuation_purpose",
    "asset_type",
    "source",
    "valuation_staff",
    "valuation_branch",
    "office",
}


def _dedupe(values):
    seen = set()
    result = []
    for value in values or []:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def load_custom_form_options(path: str | Path = CUSTOM_FORM_OPTIONS_PATH) -> dict[str, list[str]]:
    options_path = Path(path)
    if not options_path.exists():
        return {}
    try:
        data = json.loads(options_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        field: _dedupe(values)
        for field, values in data.items()
        if field in ALLOWED_OPTION_FIELDS and isinstance(values, list)
    }


def merge_custom_form_options(options: dict, path: str | Path = CUSTOM_FORM_OPTIONS_PATH) -> dict:
    merged = dict(options or {})
    custom_options = load_custom_form_options(path)
    for field, custom_values in custom_options.items():
        merged[field] = _dedupe([*(merged.get(field) or []), *custom_values])
    return merged


def add_custom_form_option(
    field: str,
    value: str,
    path: str | Path = CUSTOM_FORM_OPTIONS_PATH,
) -> list[str]:
    field = str(field or "").strip()
    value = str(value or "").strip()
    if field not in ALLOWED_OPTION_FIELDS:
        raise ValueError("Trường tùy chọn không hợp lệ")
    if not value:
        raise ValueError("Giá trị không được để trống")

    options_path = Path(path)
    options = load_custom_form_options(options_path)
    values = _dedupe([*(options.get(field) or []), value])
    options[field] = values
    options_path.parent.mkdir(parents=True, exist_ok=True)
    options_path.write_text(
        json.dumps(options, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return values
