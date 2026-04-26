from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.app_config import apply_extraction_to_form
from src.extractor import extract_land_certificate
from src.gemini_extractor import extract_land_certificate_with_gemini


def run_ocr_extraction(
    *,
    preview_path: Path,
    ai_provider: str,
    api_key: str,
    model: str,
    remember_ai_config: Callable[[], None],
):
    if ai_provider == "Gemini":
        extraction = extract_land_certificate_with_gemini(
            preview_path,
            api_key=api_key,
            model=model,
        )
    else:
        extraction = extract_land_certificate(
            preview_path,
            api_key=api_key,
            model=model,
        )
    apply_extraction_to_form(extraction)
    remember_ai_config()
    return extraction


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
