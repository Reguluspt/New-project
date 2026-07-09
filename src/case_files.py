from __future__ import annotations

import re
import shutil
from pathlib import Path

from src.contracts import short_contract_number


INVALID_PATH_CHARS = r'<>:"/\|?*'


def sanitize_folder_name(value: str, *, fallback: str) -> str:
    text = (value or "").strip() or fallback
    for char in INVALID_PATH_CHARS:
        text = text.replace(char, "-")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"-+", "-", text)
    return text[:120] or fallback


def clean_customer_folder_name(value: str) -> str:
    text = value or ""
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b0\d{8,10}\b", "", text)
    text = re.sub(r"\b\d{9,12}\b", "", text)
    text = re.sub(r"\s*[-–]\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -–")
    return text


def case_folder(
    base_dir: str | Path,
    *,
    case_id: int,
    contract_number: str = "",
    customer_name: str = "",
) -> Path:
    contract = sanitize_folder_name(contract_number, fallback=f"HS-{case_id:05d}")
    customer = sanitize_folder_name(clean_customer_folder_name(customer_name), fallback="")
    folder_name = f"{contract} - {customer}" if customer else contract
    return Path(base_dir) / folder_name


def word_export_folder(
    base_dir: str | Path,
    *,
    case_id: int,
    contract_number: str = "",
    customer_name: str = "",
    customer_type: str = "",
    organization_abbreviation: str = "",
) -> Path:
    short_contract = short_contract_number(contract_number, fallback=f"HS-{case_id:05d}")
    contract = sanitize_folder_name(short_contract, fallback=f"HS-{case_id:05d}")
    display_customer = (
        organization_abbreviation
        if str(customer_type or "").strip() == "organization" and organization_abbreviation
        else customer_name
    )
    customer = sanitize_folder_name(clean_customer_folder_name(display_customer), fallback="")
    folder_name = f"{contract} - {customer}" if customer else contract
    return Path(base_dir) / folder_name


def save_original_file(
    source_path: str | Path | None,
    original_name: str,
    folder: str | Path,
) -> Path | None:
    if not source_path:
        return None
    source = Path(source_path)
    if not source.exists():
        return None

    target_dir = Path(folder) / "originals"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = sanitize_folder_name(original_name or source.name, fallback=source.name)
    target = target_dir / target_name
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        counter = 2
        while target.exists():
            target = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    shutil.copy2(source, target)
    return target
