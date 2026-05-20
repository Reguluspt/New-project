from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.excel_writer import compose_asset_description
from src.models import LandCertificateExtraction
from src.ocr_accumulator import apply_multi_extraction_to_form, multi_extraction_to_form_state
from src.preview import detect_text_rotation_for_path
from src.sqlite_store import DEFAULT_CASE_STATUS

# ── Path constants ───────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TEMPLATE = ROOT / "samples" / "form_nhap_lieu.xlsx"
SAMPLE_DATABASE = ROOT / "samples" / "database.xlsx"
DATA_DIR = ROOT / "data"
SQLITE_DATABASE = DATA_DIR / "cases.db"
CASE_FILES_DIR = DATA_DIR / "case_files"
INDIVIDUAL_TEMPLATE_DIR = ROOT / "samples" / "templates" / "individual"
ORGANIZATION_TEMPLATE_DIR = ROOT / "samples" / "templates" / "organization"
OUTPUT_DIR = ROOT / "outputs"
CASE_EXPORT_DIR = OUTPUT_DIR / "case_exports"
UNPAID_STATUS = "Chưa thanh toán"
TEMPLATE_CONFIG_PATH = DATA_DIR / "template_config.json"
TEMPLATE_HISTORY_PATH = DATA_DIR / "template_edit_history.jsonl"
TEMPLATE_VERSIONS_DIR = DATA_DIR / "template_versions"
AI_CONFIG_PATH = DATA_DIR / "ai_config.json"
CASE_TABLE_CONFIG_PATH = DATA_DIR / "case_table_config.json"
CASE_OUTPUT_CONFIG_PATH = DATA_DIR / "case_output_config.json"

# ── Default configs ──────────────────────────────────────────────────────────

DEFAULT_TEMPLATE_CONFIG = {
    "excel_template_path": str(SAMPLE_TEMPLATE),
    "individual_template_dir": str(INDIVIDUAL_TEMPLATE_DIR),
    "organization_template_dir": str(ORGANIZATION_TEMPLATE_DIR),
    "template_editor_name": os.getenv("USERNAME", "Unknown"),
    "locked_templates": [],
    "template_labels": {},
}
DEFAULT_AI_CONFIG = {
    "provider": "Gemini",
    "providers": {
        "Gemini": {"api_key": "", "model": "gemini-2.5-flash"},
        "OpenAI": {"api_key": "", "model": "gpt-4.1-mini"},
    },
}
AUTO_ROTATION_CACHE_VERSION = "v2"
ENTRY_FORM_DEFAULTS = {
    "entry_customer_type": "individual",
    "entry_case_status": DEFAULT_CASE_STATUS,
    "entry_execution_month": datetime.now().strftime("%m/%Y"),
    "entry_payment_status": UNPAID_STATUS,
    "entry_contract_number": "",
    "entry_contract_number_ind": "",
    "entry_contract_date_ind": "",
    "entry_contract_number_org": "",
    "entry_contract_date_org": "",
    "entry_asset_type": "BĐS đặc thù khác",
    "entry_asset_description": "",
    "entry_preliminary_status": "Chưa sơ bộ",
    "entry_expected_finish_date": "",
    "entry_valuation_purpose": "",
    "entry_source": "",
    "entry_customer_info": "",
    "entry_valuation_fee_number": "",
    "entry_advance_payment": "0",
    "entry_survey_cost": "0",
    "entry_business_staff": "",
    "entry_valuation_staff": "",
    "entry_controller": "",
    "entry_legal_note": "",
    "entry_customer_info_ind": "",
    "entry_customer_address_ind": "",
    "entry_citizen_id_ind": "",
    "entry_personal_note": "",
    "entry_tax_code": "",
    "entry_customer_info_org": "",
    "entry_customer_address_org": "",
    "entry_representative_name": "",
    "entry_representative_position": "",
    "entry_authorization_note": "",
    "entry_handover_contact_name": "",
    "entry_handover_contact_position": "",
    "entry_handover_contact_phone": "",
    "entry_so_thua": "",
    "entry_so_to": "",
    "entry_land_address": "",
    "entry_owner_name": "",
    "entry_owner_address": "",
    "entry_owner_citizen_id": "",
    "so_thua": "",
    "so_to": "",
    "land_address": "",
    "owner_name": "",
    "owner_address": "",
    "citizen_id": "",
}


# ── AI config helpers ────────────────────────────────────────────────────────


def load_ai_config(config_path: str | Path) -> dict[str, object]:
    path = Path(config_path)
    config = dict(DEFAULT_AI_CONFIG)
    config["providers"] = {
        provider: dict(values)
        for provider, values in DEFAULT_AI_CONFIG["providers"].items()
    }
    if not path.exists():
        return config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config

    provider = str(data.get("provider") or config["provider"]).strip()
    if provider in config["providers"]:
        config["provider"] = provider

    saved_providers = data.get("providers", {})
    if isinstance(saved_providers, dict):
        for provider_name, defaults in config["providers"].items():
            saved = saved_providers.get(provider_name, {})
            if not isinstance(saved, dict):
                continue
            defaults["api_key"] = str(saved.get("api_key") or "")
            defaults["model"] = str(saved.get("model") or defaults["model"]).strip() or str(defaults["model"])
    return config


def save_ai_config(
    config_path: str | Path,
    config: dict[str, object],
    *,
    provider: str,
    api_key: str,
    model: str,
    save_api_key: bool,
) -> None:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    providers = {
        provider_name: dict(values)
        for provider_name, values in dict(config.get("providers", {})).items()
        if isinstance(values, dict)
    }
    if provider not in providers:
        providers[provider] = {}
    providers[provider]["model"] = model.strip()
    providers[provider]["api_key"] = api_key.strip() if save_api_key else ""
    payload = {"provider": provider, "providers": providers}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Session state helpers ────────────────────────────────────────────────────


def ensure_entry_form_defaults() -> None:
    for key, value in ENTRY_FORM_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def reset_entry_workspace() -> None:
    reset_prefixes = (
        "entry_",
        "preview_page_",
        "preview_mode_",
        "preview_zoom_",
        "thumb_page_",
        "toolbar_rotate_",
    )
    reset_keys = {
        "extraction",
        "uploaded_signature",
        "uploaded_path",
        "uploaded_original_name",
        "page_rotations",
        "manual_rotation_cache",
        "auto_rotation_cache",
        "rotation_lock_cache",
        "zoom_level",
        "so_thua",
        "so_to",
        "land_address",
        "owner_name",
        "owner_address",
        "citizen_id",
    }
    for key in list(st.session_state.keys()):
        if key in reset_keys or any(key.startswith(prefix) for prefix in reset_prefixes):
            st.session_state.pop(key, None)
    ensure_entry_form_defaults()


# ── File upload helpers ──────────────────────────────────────────────────────


def save_upload(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower()
    fd, name = tempfile.mkstemp(prefix="gcn_", suffix=suffix)
    path = Path(name)
    with os.fdopen(fd, "wb") as handle:
        handle.write(uploaded_file.getbuffer())
    return path


def ensure_uploaded_file_saved(uploaded_file) -> Path:
    signature = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("uploaded_signature") != signature:
        path = save_upload(uploaded_file)
        st.session_state.uploaded_signature = signature
        st.session_state.uploaded_path = str(path)
        st.session_state.uploaded_original_name = uploaded_file.name
    return Path(st.session_state["uploaded_path"])


# ── Extraction helpers ───────────────────────────────────────────────────────


def extraction_to_defaults(extraction: LandCertificateExtraction) -> dict[str, str]:
    so_thua = extraction.so_thua_dat.value.strip()
    so_to = extraction.so_to_ban_do.value.strip()
    land_address = extraction.dia_chi_thua_dat.value.strip()
    owner_name = extraction.ten_chu_so_huu_cuoi_cung.value.strip()
    owner_address = extraction.dia_chi_chu_so_huu_cuoi_cung.value.strip()
    citizen_id = extraction.so_cccd_chu_so_huu_cuoi_cung.value.strip()
    return {
        "asset_description": compose_asset_description(so_thua, so_to, land_address),
        "customer_info": owner_name,
        "customer_address": owner_address,
        "citizen_id": citizen_id,
        "personal_note": "; ".join(extraction.notes),
    }


def extraction_to_form_state(extraction: LandCertificateExtraction) -> dict[str, str]:
    defaults = extraction_to_defaults(extraction)
    return {
        "so_thua": extraction.so_thua_dat.value.strip(),
        "so_to": extraction.so_to_ban_do.value.strip(),
        "land_address": extraction.dia_chi_thua_dat.value.strip(),
        "owner_name": extraction.ten_chu_so_huu_cuoi_cung.value.strip(),
        "owner_address": extraction.dia_chi_chu_so_huu_cuoi_cung.value.strip(),
        "citizen_id": extraction.so_cccd_chu_so_huu_cuoi_cung.value.strip(),
        "entry_asset_description": defaults["asset_description"],
        "entry_customer_info_ind": defaults["customer_info"],
        "entry_customer_address_ind": defaults["customer_address"],
        "entry_citizen_id_ind": defaults["citizen_id"],
        "entry_customer_info": defaults["customer_info"],
        "entry_customer_address": defaults["customer_address"],
        "entry_citizen_id": defaults["citizen_id"],
        "entry_personal_note": defaults["personal_note"],
    }


def apply_extraction_to_form(extraction: LandCertificateExtraction) -> None:
    for key, value in multi_extraction_to_form_state(extraction).items():
        st.session_state[key] = value


def apply_extraction_collection_to_form(extraction: object, *, append: bool = True) -> int:
    return apply_multi_extraction_to_form(extraction, append=append)


# ── Rotation cache helpers ───────────────────────────────────────────────────


def get_auto_rotation(preview_path: Path, *, page_number: int) -> int:
    auto_key = f"auto_rotation::{AUTO_ROTATION_CACHE_VERSION}::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("auto_rotation_cache", {})
    if auto_key not in cache:
        cache[auto_key] = detect_text_rotation_for_path(preview_path, page_number=page_number)
    return int(cache[auto_key])


def ensure_auto_rotations(preview_path: Path, *, total_pages: int, force: bool = False) -> dict[int, int]:
    rotations: dict[int, int] = {}
    cache = st.session_state.setdefault("auto_rotation_cache", {})
    for page_number in range(1, total_pages + 1):
        auto_key = f"auto_rotation::{AUTO_ROTATION_CACHE_VERSION}::{preview_path.resolve()}::{page_number}"
        if force and is_rotation_locked(preview_path, page_number=page_number):
            rotations[page_number] = int(cache.get(auto_key, 0))
            continue
        if force or auto_key not in cache:
            cache[auto_key] = detect_text_rotation_for_path(preview_path, page_number=page_number)
        rotations[page_number] = int(cache.get(auto_key, 0))
    return rotations


def refresh_auto_rotation(preview_path: Path, *, page_number: int) -> int:
    auto_key = f"auto_rotation::{AUTO_ROTATION_CACHE_VERSION}::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("auto_rotation_cache", {})
    if is_rotation_locked(preview_path, page_number=page_number):
        return int(cache.get(auto_key, 0))
    cache[auto_key] = detect_text_rotation_for_path(preview_path, page_number=page_number)
    return int(cache[auto_key])


def refresh_all_auto_rotations(preview_path: Path, *, total_pages: int) -> dict[int, int]:
    return ensure_auto_rotations(preview_path, total_pages=total_pages, force=True)


def get_manual_rotation(preview_path: Path, *, page_number: int) -> int:
    manual_key = f"manual_rotation::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("manual_rotation_cache", {})
    return int(cache.get(manual_key, 0))


def adjust_manual_rotation(preview_path: Path, *, page_number: int, delta: int) -> int:
    manual_key = f"manual_rotation::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("manual_rotation_cache", {})
    cache[manual_key] = (int(cache.get(manual_key, 0)) + delta) % 360
    return int(cache[manual_key])


def reset_manual_rotation(preview_path: Path, *, page_number: int) -> None:
    manual_key = f"manual_rotation::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("manual_rotation_cache", {})
    cache[manual_key] = 0


def reset_all_manual_rotations(preview_path: Path, *, total_pages: int) -> None:
    for page_number in range(1, total_pages + 1):
        reset_manual_rotation(preview_path, page_number=page_number)


def is_rotation_locked(preview_path: Path, *, page_number: int) -> bool:
    lock_key = f"rotation_lock::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("rotation_lock_cache", {})
    return bool(cache.get(lock_key, False))


def set_rotation_lock(preview_path: Path, *, page_number: int, locked: bool) -> bool:
    lock_key = f"rotation_lock::{preview_path.resolve()}::{page_number}"
    cache = st.session_state.setdefault("rotation_lock_cache", {})
    cache[lock_key] = bool(locked)
    return bool(cache[lock_key])


def select_pdf_preview_page(preview_name: str, *, thumb_page: int, total_pages: int) -> None:
    page_key = f"preview_page_{preview_name}"
    mode_key = f"preview_mode_{preview_name}"
    view_mode = st.session_state.get(mode_key, "1 trang")
    if view_mode == "2 trang" and total_pages > 1:
        target_page = thumb_page if thumb_page < total_pages else total_pages - 1
    else:
        target_page = thumb_page
    st.session_state[page_key] = max(1, min(int(target_page), max(total_pages, 1)))


# ── Form sync helpers ────────────────────────────────────────────────────────


def sync_gcn_to_form() -> None:
    st.session_state["entry_asset_description"] = compose_asset_description(
        st.session_state.get("so_thua", "").strip(),
        st.session_state.get("so_to", "").strip(),
        st.session_state.get("land_address", "").strip(),
    )
    st.session_state["entry_customer_info_ind"] = st.session_state.get("owner_name", "").strip()
    st.session_state["entry_customer_address_ind"] = st.session_state.get("owner_address", "").strip()
    st.session_state["entry_citizen_id_ind"] = st.session_state.get("citizen_id", "").strip()


def sync_gcn_to_form_from_fields() -> None:
    sync_gcn_to_form()


import re as _re


def _extract_first_match(pattern: str, text: str) -> str:
    match = _re.search(pattern, text, flags=_re.IGNORECASE)
    return match.group(1).strip(" .;,") if match else ""


def parse_asset_description_fields(text: str) -> dict[str, str]:
    value = (text or "").strip()
    return {
        "so_thua": _extract_first_match(r"th(?:ửa|ua)\s+(?:đất|dat)\s+s(?:ố|o)\s+([^,;.\n]+)", value),
        "so_to": _extract_first_match(r"t(?:ờ|o)\s+(?:bản|ban)\s+(?:đồ|do)\s+s(?:ố|o)\s+([^,;.\n]+)", value),
        "land_address": _extract_first_match(r"t(?:ại|ai)\s+(?:địa|dia)\s+(?:chỉ|chi)\s+(.+)", value),
    }


def sync_form_to_gcn() -> list[str]:
    st.session_state["owner_name"] = st.session_state.get("entry_customer_info_ind", "").strip()
    st.session_state["owner_address"] = st.session_state.get("entry_customer_address_ind", "").strip()
    st.session_state["citizen_id"] = st.session_state.get("entry_citizen_id_ind", "").strip()

    parsed = parse_asset_description_fields(st.session_state.get("entry_asset_description", ""))
    updated_fields: list[str] = []
    if parsed["so_thua"]:
        st.session_state["so_thua"] = parsed["so_thua"]
        updated_fields.append("so thua")
    if parsed["so_to"]:
        st.session_state["so_to"] = parsed["so_to"]
        updated_fields.append("so to")
    if parsed["land_address"]:
        st.session_state["land_address"] = parsed["land_address"]
        updated_fields.append("dia chi thua dat")
    return updated_fields


def sync_form_to_gcn_from_fields() -> None:
    sync_form_to_gcn()


# ── UI helpers shared across pages ───────────────────────────────────────────


def render_confidence_row(label: str, value, key: str, on_change=None) -> str:
    confidence = int(value.confidence * 100)
    evidence = value.evidence.strip()
    text = st.text_input(label, value=value.value, key=key, on_change=on_change)
    st.caption(f"Độ tin cậy: {confidence}% | Bằng chứng: {evidence or 'Chưa có'}")
    return text


def options_with_current(options: list[str], current_value: str) -> list[str]:
    cleaned = [str(option).strip() for option in options if str(option).strip()]
    if current_value and current_value not in cleaned:
        return [current_value, "", *cleaned]
    if current_value:
        return cleaned
    return ["", *cleaned]


def selectbox_from_excel(label: str, field_key: str, options: dict[str, list[str]], session_key: str) -> str:
    current_value = str(st.session_state.get(session_key, "") or "").strip()
    field_options = options_with_current(options.get(field_key, []), current_value)
    if session_key not in st.session_state or current_value not in field_options:
        st.session_state[session_key] = field_options[0]
    return st.selectbox(label, field_options, key=session_key)
