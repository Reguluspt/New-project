from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from views import entry_actions, entry_form, entry_viewer


def render(
    *,
    sqlite_db_path: Path,
    excel_template_path: Path,
    excel_dropdown_options: dict,
    ai_provider: str,
    api_key: str,
    model: str,
    api_key_label: str,
    remember_ai_config: Callable[[], None],
) -> None:
    uploaded_file = st.file_uploader(
        "Tải lên PDF hoặc ảnh Giấy chứng nhận quyền sử dụng đất",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
    )

    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        preview_path, using_sample = entry_viewer.render(uploaded_file)
        entry_actions.render_ocr_action(
            uploaded_file=uploaded_file,
            preview_path=preview_path,
            using_sample=using_sample,
            ai_provider=ai_provider,
            api_key=api_key,
            model=model,
            api_key_label=api_key_label,
            remember_ai_config=remember_ai_config,
        )

    with right:
        entry_form.render(
            sqlite_db_path=sqlite_db_path,
            excel_template_path=excel_template_path,
            excel_dropdown_options=excel_dropdown_options,
        )
