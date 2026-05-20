from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from src.excel_writer import compose_asset_description
from src.models import LandCertificateExtraction, LandCertificateMultiExtraction, blank_extraction


MULTILINE_FORM_KEYS = {
    "so_thua_dat": "entry_so_thua",
    "so_to_ban_do": "entry_so_to",
    "dia_chi_thua_dat": "entry_land_address",
    "owner_name": "entry_owner_name",
    "owner_address": "entry_owner_address",
    "owner_citizen_id": "entry_owner_citizen_id",
    "asset_description": "entry_asset_description",
}


def normalize_multi_extraction(extraction: object) -> LandCertificateMultiExtraction:
    if isinstance(extraction, LandCertificateMultiExtraction):
        return extraction
    if isinstance(extraction, LandCertificateExtraction):
        return LandCertificateMultiExtraction(assets=[extraction])
    if hasattr(extraction, "assets"):
        assets = list(getattr(extraction, "assets") or [])
        return LandCertificateMultiExtraction(assets=assets)
    return LandCertificateMultiExtraction(assets=[blank_extraction()])


def _clean(value: object) -> str:
    return str(value or "").strip()


def _extracted_value(asset: LandCertificateExtraction, field: str) -> str:
    value = getattr(asset, field)
    return _clean(getattr(value, "value", ""))


def _dedupe_assets(assets: Iterable[LandCertificateExtraction]) -> list[LandCertificateExtraction]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[LandCertificateExtraction] = []
    for asset in assets:
        identity = (
            _extracted_value(asset, "so_thua_dat").lower(),
            _extracted_value(asset, "so_to_ban_do").lower(),
            _extracted_value(asset, "dia_chi_thua_dat").lower(),
            _extracted_value(asset, "ten_chu_so_huu_cuoi_cung").lower(),
        )
        if not any(identity) or identity in seen:
            continue
        seen.add(identity)
        unique.append(asset)
    return unique


def multi_extraction_to_form_state(extraction: object) -> dict[str, str]:
    multi = normalize_multi_extraction(extraction)
    assets = _dedupe_assets(multi.assets)
    if not assets:
        assets = [blank_extraction()]

    so_thua_lines: list[str] = []
    so_to_lines: list[str] = []
    land_address_lines: list[str] = []
    owner_name_lines: list[str] = []
    owner_address_lines: list[str] = []
    citizen_id_lines: list[str] = []
    asset_description_lines: list[str] = []
    note_lines: list[str] = []

    for asset in assets:
        so_thua = _extracted_value(asset, "so_thua_dat")
        so_to = _extracted_value(asset, "so_to_ban_do")
        land_address = _extracted_value(asset, "dia_chi_thua_dat")
        owner_name = _extracted_value(asset, "ten_chu_so_huu_cuoi_cung")
        owner_address = _extracted_value(asset, "dia_chi_chu_so_huu_cuoi_cung")
        citizen_id = _extracted_value(asset, "so_cccd_chu_so_huu_cuoi_cung")

        so_thua_lines.append(so_thua)
        so_to_lines.append(so_to)
        land_address_lines.append(land_address)
        owner_name_lines.append(owner_name)
        owner_address_lines.append(owner_address)
        citizen_id_lines.append(citizen_id)
        asset_description_lines.append(compose_asset_description(so_thua, so_to, land_address))
        note_lines.extend(_clean(note) for note in asset.notes if _clean(note))

    return {
        "so_thua": "\n".join(line for line in so_thua_lines if line),
        "so_to": "\n".join(line for line in so_to_lines if line),
        "land_address": "\n".join(line for line in land_address_lines if line),
        "owner_name": "\n".join(line for line in owner_name_lines if line),
        "owner_address": "\n".join(line for line in owner_address_lines if line),
        "citizen_id": "\n".join(line for line in citizen_id_lines if line),
        "entry_so_thua": "\n".join(line for line in so_thua_lines if line),
        "entry_so_to": "\n".join(line for line in so_to_lines if line),
        "entry_land_address": "\n".join(line for line in land_address_lines if line),
        "entry_owner_name": "\n".join(line for line in owner_name_lines if line),
        "entry_owner_address": "\n".join(line for line in owner_address_lines if line),
        "entry_owner_citizen_id": "\n".join(line for line in citizen_id_lines if line),
        "entry_asset_description": "\n".join(line for line in asset_description_lines if line),
        "entry_personal_note": "; ".join(note_lines),
        "entry_customer_info_ind": owner_name_lines[0] if owner_name_lines else "",
        "entry_customer_address_ind": owner_address_lines[0] if owner_address_lines else "",
        "entry_citizen_id_ind": citizen_id_lines[0] if citizen_id_lines else "",
        "entry_customer_info": owner_name_lines[0] if owner_name_lines else "",
        "entry_customer_address": owner_address_lines[0] if owner_address_lines else "",
        "entry_citizen_id": citizen_id_lines[0] if citizen_id_lines else "",
    }


def _merge_multiline(existing: str, incoming: str) -> str:
    existing_lines = [_clean(line) for line in str(existing or "").splitlines() if _clean(line)]
    incoming_lines = [_clean(line) for line in str(incoming or "").splitlines() if _clean(line)]
    merged = list(existing_lines)
    normalized = {line.lower() for line in merged}
    for line in incoming_lines:
        if line.lower() not in normalized:
            merged.append(line)
            normalized.add(line.lower())
    return "\n".join(merged)


def apply_multi_extraction_to_form(extraction: object, *, append: bool = True) -> int:
    multi = normalize_multi_extraction(extraction)
    state = multi_extraction_to_form_state(multi)
    multiline_keys = {
        "so_thua",
        "so_to",
        "land_address",
        "owner_name",
        "owner_address",
        "citizen_id",
        "entry_so_thua",
        "entry_so_to",
        "entry_land_address",
        "entry_owner_name",
        "entry_owner_address",
        "entry_owner_citizen_id",
        "entry_asset_description",
    }

    for key, value in state.items():
        if not value:
            continue
        if append and key in multiline_keys:
            st.session_state[key] = _merge_multiline(st.session_state.get(key, ""), value)
        elif key.startswith("entry_customer") or key in {"entry_citizen_id_ind", "entry_citizen_id"}:
            st.session_state.setdefault(key, "")
            if not _clean(st.session_state.get(key)):
                st.session_state[key] = value
        elif append and key == "entry_personal_note":
            st.session_state[key] = _merge_multiline(st.session_state.get(key, ""), value)
        else:
            st.session_state[key] = value
    return len(_dedupe_assets(multi.assets))
