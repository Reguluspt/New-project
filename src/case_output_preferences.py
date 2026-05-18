from __future__ import annotations

import json
import os
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
    if not value:
        return Path(default_dir)

    # Check if Windows absolute path on Linux
    is_cross_os = ":" in value and os.name == "posix"
    if is_cross_os:
        # Try to heal using standard folder names
        unified = value.replace("\\", "/")
        parts = unified.split("/")
        root_dir = Path(__file__).resolve().parent.parent
        for marker in ["samples", "data", "outputs", "exports"]:
            if marker in parts:
                idx = parts.index(marker)
                rel_path = "/".join(parts[idx:])
                healed_path = root_dir / rel_path
                try:
                    healed_path.mkdir(parents=True, exist_ok=True)
                    return healed_path
                except Exception:
                    pass
        return Path(default_dir)

    loaded_path = Path(value)
    try:
        if not loaded_path.exists():
            # Try to heal or create it
            unified = value.replace("\\", "/")
            parts = unified.split("/")
            root_dir = Path(__file__).resolve().parent.parent
            healed = False
            for marker in ["samples", "data", "outputs", "exports"]:
                if marker in parts:
                    idx = parts.index(marker)
                    rel_path = "/".join(parts[idx:])
                    healed_path = root_dir / rel_path
                    try:
                        healed_path.mkdir(parents=True, exist_ok=True)
                        loaded_path = healed_path
                        healed = True
                        break
                    except Exception:
                        pass
            if not healed:
                try:
                    loaded_path.mkdir(parents=True, exist_ok=True)
                except Exception:
                    return Path(default_dir)
    except Exception:
        return Path(default_dir)

    return loaded_path


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
