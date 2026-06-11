from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.app_config import DATA_DIR
from src.upload_queue import make_queue_items, upload_batch_signature
from views import entry_actions, entry_form, entry_viewer


def _render_entry_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                max-width: none !important;
                width: 100% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .entry-title {
                margin: 0;
                color: var(--app-text);
                font-size: 32px;
                line-height: 38px;
                font-weight: 760;
            }
            .entry-caption {
                margin: 4px 0 14px;
                color: var(--app-muted);
                font-size: 13px;
                line-height: 1.45;
            }
            .entry-section-label {
                margin: 0 0 8px;
                color: #64748b;
                font-size: 11px;
                font-weight: 800;
                text-transform: uppercase;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-entry_viewer_panel):has(.st-key-entry_form_panel) {
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) 860px !important;
                align-items: start !important;
                gap: 1rem !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-entry_viewer_panel):has(.st-key-entry_form_panel) > div[data-testid="stColumn"] {
                width: auto !important;
                min-width: 0 !important;
            }
            .st-key-entry_form_panel {
                width: 860px !important;
                min-width: 860px !important;
                max-width: 860px !important;
                margin-left: auto !important;
                box-sizing: border-box !important;
                overflow: hidden !important;
            }
            .st-key-entry_form_panel *,
            .st-key-entry_form_panel *::before,
            .st-key-entry_form_panel *::after {
                box-sizing: border-box !important;
            }
            .st-key-entry_form_panel > div,
            .st-key-entry_form_panel div[data-testid="stVerticalBlockBorderWrapper"],
            .st-key-entry_form_panel div[data-testid="stVerticalBlock"],
            .st-key-entry_form_panel div[data-testid="stHorizontalBlock"] {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
            }
            .st-key-entry_form_panel div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                width: auto !important;
                max-width: 100% !important;
                min-width: 0 !important;
            }
            .st-key-entry_form_panel div[data-testid="stTextInput"],
            .st-key-entry_form_panel div[data-testid="stTextArea"],
            .st-key-entry_form_panel div[data-baseweb="select"],
            .st-key-entry_form_panel div[data-testid="stSelectbox"] {
                max-width: 100% !important;
                min-width: 0 !important;
            }
            .st-key-entry_form_panel div[data-testid="stTextInput"] input,
            .st-key-entry_form_panel textarea,
            .st-key-entry_form_panel div[data-baseweb="select"] > div {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: #fff;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] h2,
            div[data-testid="stVerticalBlockBorderWrapper"] h3 {
                margin-top: 0;
                color: var(--app-text);
                font-size: 19px;
                line-height: 24px;
                font-weight: 760;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] {
                color: var(--app-muted);
            }
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stFileUploader"] section {
                border-color: var(--app-outline);
                border-radius: 12px;
                background: #f8fbff;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stTabs"] button {
                border-radius: 0;
                font-weight: 750;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stTextInput"] input,
            div[data-testid="stVerticalBlockBorderWrapper"] textarea,
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-baseweb="select"] > div {
                border-color: #cfe0f6;
                background: #f8fbff;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] label p {
                color: #64748b;
                font-size: 11px;
                font-weight: 800;
                text-transform: uppercase;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"] {
                background: var(--app-primary);
                border-color: var(--app-primary);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _accept_uploaded_files(uploaded_files) -> None:
    upload_signature = upload_batch_signature(uploaded_files)
    if not uploaded_files or st.session_state.get("entry_upload_signature") == upload_signature:
        return

    try:
        new_items = make_queue_items(uploaded_files, upload_dir=DATA_DIR / "entry_uploads")
        queue = st.session_state.setdefault("entry_upload_queue", [])
        queue.extend(new_items)
        st.session_state["entry_upload_signature"] = upload_signature
        if new_items:
            st.session_state["entry_selected_upload_id"] = new_items[0]["id"]
    except Exception as exc:
        st.error(f"Không thể nhận file tải lên: {exc}")


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
    _render_entry_styles()
    st.markdown('<h1 class="entry-title">Nhập hồ sơ</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="entry-caption">Tải GCN, quét AI, kiểm tra dữ liệu và lưu/xuất/gửi yêu cầu định giá.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="entry-section-label">Tài liệu và AI</div>', unsafe_allow_html=True)
        intake_upload_col, intake_queue_col = st.columns([0.36, 0.64], gap="large")
        with intake_upload_col:
            uploaded_files = st.file_uploader(
                "Tải lên PDF/ảnh GCN",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="entry_file_uploader",
            )
            _accept_uploaded_files(uploaded_files)

        with intake_queue_col:
            selected_preview_path = entry_actions.selected_upload_path()
            entry_actions.render_queue_ocr_action(
                preview_path=selected_preview_path,
                ai_provider=ai_provider,
                api_key=api_key,
                model=model,
                api_key_label=api_key_label,
                remember_ai_config=remember_ai_config,
            )

    preview_path = entry_actions.selected_upload_path()
    using_sample = False
    if preview_path is None:
        preview_path, using_sample = entry_viewer.get_preview_context(None)

    viewer_col, form_col = st.columns([1, 1], gap="medium")

    with viewer_col:
        with st.container(border=True, key="entry_viewer_panel"):
            entry_viewer.render(
                None,
                preview_path=preview_path,
                using_sample=using_sample,
            )

    with form_col:
        with st.container(border=True, key="entry_form_panel"):
            entry_form.render(
                sqlite_db_path=sqlite_db_path,
                excel_template_path=excel_template_path,
                excel_dropdown_options=excel_dropdown_options,
            )
