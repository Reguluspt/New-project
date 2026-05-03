from __future__ import annotations

import json
from pathlib import Path


CONFIG_KEY = "case_output_dir"


def load_case_output_dir(config_path: str | Path, *, default_dir: str | Path) -> Path:
    path = Path(config_path)
    if not path.exists():
        return Path(default_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Path(default_dir)

    value = str(data.get(CONFIG_KEY) or "").strip()
    return Path(value) if value else Path(default_dir)


def save_case_output_dir(config_path: str | Path, output_dir: str | Path) -> Path:
    raw_value = str(output_dir).strip()
    if not raw_value:
        raise ValueError("Thư mục lưu bộ hồ sơ không được để trống.")
    selected = Path(raw_value).expanduser()
    selected.mkdir(parents=True, exist_ok=True)

    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({CONFIG_KEY: str(selected)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return selected
