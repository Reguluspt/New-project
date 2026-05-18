from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import streamlit as st

from src.app_config import apply_extraction_to_form
from src.extractor import extract_land_certificate
from src.gemini_extractor import extract_land_certificate_with_gemini


def _document_page_key(preview_path: Path, page_number: int) -> str:
    return f"{preview_path.resolve()}::{page_number}"


def _normalize_rotation(value: Any) -> int | None:
    try:
        angle = int(round(float(value))) % 360
    except (TypeError, ValueError):
        return None
    return angle if angle in {0, 90, 180, 270} else None


def apply_gemini_page_metadata_to_viewer(preview_path: Path, extraction: object) -> bool:
    metadata = getattr(extraction, "page_metadata", None)
    if not metadata:
        return False

    if isinstance(metadata, dict):
        items = metadata.items()
    elif isinstance(metadata, list):
        items = []
        for item in metadata:
            if isinstance(item, dict):
                items.append((item.get("page_number"), item.get("rotation")))
            else:
                items.append((getattr(item, "page_number", None), getattr(item, "rotation", None)))
    else:
        return False

    rotations = st.session_state.setdefault("page_rotations", {})
    updated = False
    for raw_page_number, raw_rotation in items:
        try:
            page_number = int(raw_page_number)
        except (TypeError, ValueError):
            continue
        if page_number < 1:
            continue
        rotation = _normalize_rotation(raw_rotation)
        if rotation is None:
            continue
        rotations[_document_page_key(preview_path, page_number)] = rotation
        updated = True
    return updated


def run_ocr_extraction(
    *,
    preview_path: Path,
    ai_provider: str,
    api_key: str,
    model: str,
    remember_ai_config: Callable[[], None],
):
    metadata_updated = False
    if ai_provider == "Gemini":
        extraction = extract_land_certificate_with_gemini(
            preview_path,
            api_key=api_key,
            model=model,
        )
        metadata_updated = apply_gemini_page_metadata_to_viewer(preview_path, extraction)
    else:
        extraction = extract_land_certificate(
            preview_path,
            api_key=api_key,
            model=model,
        )
    if hasattr(extraction, "assets") and extraction.assets:
        single_extraction = extraction.assets[0]
    else:
        from src.models import blank_extraction
        single_extraction = blank_extraction()

    apply_extraction_to_form(single_extraction)
    remember_ai_config()
    if metadata_updated:
        st.rerun()
    return single_extraction


def render_ocr_action(
    *,
    uploaded_file,
    preview_path: Path | None,
    using_sample: bool,
    ai_provider: str,
    api_key: str,
    model: str,
    api_key_label: str,
    remember_ai_config: Callable[[], None],
) -> None:
    if uploaded_file is not None and not using_sample:
        if st.button(f"Quét GCN bằng {ai_provider}", type="primary", width="stretch"):
            if not api_key:
                st.error(f"Cần nhập {api_key_label} trước khi quét.")
            else:
                with st.spinner("Đang gửi tài liệu đến AI và trích xuất dữ liệu..."):
                    try:
                        st.session_state.extraction = run_ocr_extraction(
                            preview_path=preview_path,
                            ai_provider=ai_provider,
                            api_key=api_key,
                            model=model,
                            remember_ai_config=remember_ai_config,
                        )
                        st.success("Đã trích xuất xong và tự điền vào form. Vui lòng kiểm tra lại bên phải.")
                    except Exception as exc:
                        st.error(f"Quét AI thất bại: {exc}")
