from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.app_config import (
    DATA_DIR,
    DEFAULT_TEMPLATE_CONFIG,
    OUTPUT_DIR,
    SAMPLE_TEMPLATE,
    SQLITE_DATABASE,
    TEMPLATE_CONFIG_PATH,
    TEMPLATE_HISTORY_PATH,
    ensure_entry_form_defaults,
)
from src.background_services import ensure_background_services
from src.auth import logout, render_login_gate
from src.database_manager import get_db_path, log_records_db_path
from src.excel_writer import load_dropdown_options
from src.models import blank_extraction
from src.sqlite_store import init_db
from src.template_manager import load_template_config
from src.ui_theme import render_app_header, render_app_theme
from views import cases as cases_view
from views import dashboard as dashboard_view
from views import entry as entry_view
from views import settings as settings_view
from views import templates as templates_view
from views import organizations_view as organizations_view
from views import delivery_view as delivery_view
from views import sobo_view as sobo_view
from src.backup_service import create_backup


def _load_ai_runtime_config() -> tuple[str, str, str, str]:
    return (
        "Gemini",
        os.getenv("GEMINI_API_KEY", "").strip(),
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        "GEMINI_API_KEY trong API.env",
    )


def _entry_excel_template_candidates(excel_template_path: Path) -> list[Path]:
    return [
        excel_template_path,
        DATA_DIR / "Form_nhap_lieu.xlsx",
        DATA_DIR / "form_nhap_lieu.xlsx",
        SAMPLE_TEMPLATE,
    ]


def _resolve_entry_excel_template_path(excel_template_path: Path) -> Path:
    for candidate in _entry_excel_template_candidates(excel_template_path):
        if candidate.exists():
            return candidate
    return excel_template_path


def _load_entry_dropdown_options(excel_template_path: Path) -> dict[str, list[str]]:
    options: dict[str, list[str]] = {}
    for candidate in _entry_excel_template_candidates(excel_template_path):
        if not candidate.exists():
            continue
        try:
            candidate_options = load_dropdown_options(candidate)
        except Exception:
            continue
        for field_key, values in candidate_options.items():
            if not options.get(field_key):
                options[field_key] = values
    return options


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / "API.env", override=True)
    st.set_page_config(
        page_title="Hệ thống thẩm định nội bộ",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_app_theme()

    guest_user = os.getenv("APP_GUEST_USERNAME", "khach").strip()

    # Bypass login gate for users accessing via direct public view link
    view_param = st.query_params.get("view")
    if view_param == "sobo":
        st.session_state["app_authenticated"] = True
        st.session_state["app_login_username"] = guest_user
        st.session_state["active_view"] = "sobo"

    if not render_login_gate():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Global OAuth2 Authorization Callback Handler
    if "oauth_success_provider" in st.session_state:
        prov = st.session_state.pop("oauth_success_provider")
        st.toast(f"🎉 Liên kết thành công tài khoản {prov.upper()}!", icon="✅")
        st.success(f"🎉 Chúc mừng! Kết nối thành công tài khoản {prov.upper()} OAuth2.")
        st.balloons()

    code = st.query_params.get("code")
    state = st.query_params.get("state")
    oauth_provider = st.query_params.get("oauth_provider") or state
    if code and oauth_provider:
        try:
            from src.oauth2_service import load_oauth_config, exchange_code_for_tokens
            oauth_config = load_oauth_config()
            redirect_uri = oauth_config.get("redirect_uri", "http://localhost:8501/")
            
            exchange_code_for_tokens(oauth_provider, code, redirect_uri)
            st.session_state["oauth_success_provider"] = oauth_provider
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Kết nối OAuth2 thất bại: {e}")
            st.info(f"💡 Gợi ý: Hãy kiểm tra lại Client Secret hoặc Redirect URI trên Google Cloud Console xem đã khớp 100% với '{redirect_uri}' chưa.")

    # Silent backup once per session
    if "startup_backup_done" not in st.session_state:
        try:
            create_backup(DATA_DIR)
            st.session_state["startup_backup_done"] = True
        except Exception as exc:
            # Ghi nhận lỗi nhưng không chặn người dùng tiếp tục
            print(f"[{datetime.now()}] Lỗi sao lưu tự động: {exc}")

    ensure_background_services()
    records_db_path = Path(get_db_path())
    log_records_db_path("streamlit_app", records_db_path)

    template_config = load_template_config(TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG)
    configured_excel_template_path = Path(str(template_config["excel_template_path"]))
    excel_template_path = _resolve_entry_excel_template_path(configured_excel_template_path)
    individual_template_dir = Path(str(template_config["individual_template_dir"]))
    organization_template_dir = Path(str(template_config["organization_template_dir"]))
    current_user = str(template_config.get("template_editor_name") or os.getenv("USERNAME", "Unknown"))
    try:
        excel_dropdown_options = _load_entry_dropdown_options(configured_excel_template_path)
    except Exception as exc:
        excel_dropdown_options = {}
        st.warning(f"Không đọc được danh sách chọn từ file Excel mẫu: {exc}")

    sqlite_db_path = SQLITE_DATABASE
    init_db(sqlite_db_path)
    ai_provider, api_key, model, api_key_label = _load_ai_runtime_config()

    active_view = str(st.session_state.get("active_view") or "dashboard")
    is_guest = (st.session_state.get("app_login_username") == guest_user)
    if is_guest and active_view != "sobo":
        active_view = "sobo"
        st.session_state["active_view"] = "sobo"

    active_view = render_app_header(current_user, active_view, on_logout=logout)

    if "extraction" not in st.session_state:
        st.session_state.extraction = blank_extraction()
    if "uploaded_path" not in st.session_state:
        st.session_state.uploaded_path = None
    if "uploaded_original_name" not in st.session_state:
        st.session_state.uploaded_original_name = ""
    if "uploaded_signature" not in st.session_state:
        st.session_state.uploaded_signature = ""
    ensure_entry_form_defaults()

    if active_view == "dashboard":
        dashboard_view.render(sqlite_db_path)

    elif active_view == "entry":
        entry_view.render(
            sqlite_db_path=sqlite_db_path,
            excel_template_path=excel_template_path,
            excel_dropdown_options=excel_dropdown_options,
            ai_provider=ai_provider,
            api_key=api_key,
            model=model,
            api_key_label=api_key_label,
            remember_ai_config=lambda: None,
        )

    elif active_view == "cases":
        cases_view.render(
            sqlite_db_path,
            records_db_path,
            individual_template_dir,
            organization_template_dir,
        )

    elif active_view == "organizations":
        organizations_view.render(sqlite_db_path, api_key, model)

    elif active_view == "delivery":
        delivery_view.render(records_db_path)

    elif active_view == "sobo":
        sobo_view.render(records_db_path, is_guest=is_guest)

    elif active_view == "templates":
        templates_view.render(
            TEMPLATE_CONFIG_PATH,
            template_config,
            TEMPLATE_HISTORY_PATH,
        )

    elif active_view == "settings":
        settings_view.render(
            TEMPLATE_CONFIG_PATH,
            template_config,
        )


if __name__ == "__main__":
    main()
