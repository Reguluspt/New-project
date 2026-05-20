from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.app_config import DATA_DIR
from src.upload_queue import make_queue_items, upload_batch_signature
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
    uploaded_files = st.file_uploader(
        "Tải lên một hoặc nhiều file PDF/ảnh GCN",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="entry_file_uploader",
    )

    upload_signature = upload_batch_signature(uploaded_files)
    if uploaded_files and st.session_state.get("entry_upload_signature") != upload_signature:
        try:
            new_items = make_queue_items(uploaded_files, upload_dir=DATA_DIR / "entry_uploads")
            queue = st.session_state.setdefault("entry_upload_queue", [])
            queue.extend(new_items)
            st.session_state["entry_upload_signature"] = upload_signature
            if new_items:
                st.session_state["entry_selected_upload_id"] = new_items[0]["id"]
        except Exception as exc:
            st.error(f"Không thể nhận file tải lên: {exc}")

    preview_path = entry_actions.selected_upload_path()
    using_sample = False
    if preview_path is None:
        preview_path, using_sample = entry_viewer.get_preview_context(None)

    entry_actions.render_queue_ocr_action(
        preview_path=preview_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        api_key_label=api_key_label,
        remember_ai_config=remember_ai_config,
    )

    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        entry_viewer.render(
            None,
            preview_path=preview_path,
            using_sample=using_sample,
        )

    with right:
        entry_form.render(
            sqlite_db_path=sqlite_db_path,
            excel_template_path=excel_template_path,
            excel_dropdown_options=excel_dropdown_options,
        )
