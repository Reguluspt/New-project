from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

MIN_COLUMN_WIDTH = 0.15
MAX_COLUMN_WIDTH = 2.5


def _clamp_width(value: object, default: float) -> float:
    try:
        width = float(value)
    except (TypeError, ValueError):
        return default
    return min(MAX_COLUMN_WIDTH, max(MIN_COLUMN_WIDTH, width))


def load_column_widths(path: str | Path, defaults: Mapping[str, float]) -> dict[str, float]:
    config_path = Path(path)
    widths = {key: float(value) for key, value in defaults.items()}
    if not config_path.exists():
        return widths
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return widths

    saved_widths = payload.get("column_widths", {})
    if not isinstance(saved_widths, dict):
        return widths

    for key, default in defaults.items():
        if key in saved_widths:
            widths[key] = _clamp_width(saved_widths[key], float(default))
    return widths


def save_column_widths(path: str | Path, widths: Mapping[str, float]) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "column_widths": {
            key: _clamp_width(value, 1.0)
            for key, value in widths.items()
        }
    }
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
