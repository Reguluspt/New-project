from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.app_config import (
    AI_CONFIG_PATH,
    DATA_DIR,
    DEFAULT_TEMPLATE_CONFIG,
    OUTPUT_DIR,
    TEMPLATE_CONFIG_PATH,
    TEMPLATE_HISTORY_PATH,
    ensure_entry_form_defaults,
    load_ai_config,
)
from src.background_services import ensure_background_services
from src.database_manager import get_db_path, log_records_db_path
from src.excel_writer import load_dropdown_options
from src.models import blank_extraction
from src.template_manager import load_template_config
from src.ui_theme import render_app_header, render_app_theme
from views import cases as cases_view
from views import dashboard as dashboard_view
from views import entry as entry_view
from views import settings as settings_view
from views import sidebar as sidebar_view
from views import templates as templates_view


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / "API.env")
    load_dotenv()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_background_services()
    records_db_path = Path(get_db_path())
    log_records_db_path("streamlit_app", records_db_path)
    st.set_page_config(
        page_title="Há»‡ thá»‘ng tháº©m Ä‘á»‹nh ná»™i bá»™",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_app_theme()

    template_config = load_template_config(TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG)
    ai_config = load_ai_config(AI_CONFIG_PATH)
    excel_template_path = Path(str(template_config["excel_template_path"]))
    individual_template_dir = Path(str(template_config["individual_template_dir"]))
    organization_template_dir = Path(str(template_config["organization_template_dir"]))
    current_user = str(template_config.get("template_editor_name") or os.getenv("USERNAME", "Unknown"))
    try:
        excel_dropdown_options = load_dropdown_options(excel_template_path) if excel_template_path.exists() else {}
    except Exception as exc:
        excel_dropdown_options = {}
        st.warning(f"KhÃ´ng Ä‘á»c Ä‘Æ°á»£c danh sÃ¡ch chá»n tá»« file Excel máº«u: {exc}")

    sidebar_state = sidebar_view.render(
        ai_config=ai_config,
        excel_template_path=excel_template_path,
        individual_template_dir=individual_template_dir,
        organization_template_dir=organization_template_dir,
    )
    sqlite_db_path = Path(sidebar_state["sqlite_db_path"])
    ai_provider = str(sidebar_state["ai_provider"])
    api_key = str(sidebar_state["api_key"])
    model = str(sidebar_state["model"])
    api_key_label = str(sidebar_state["api_key_label"])
    remember_current_ai_config = sidebar_state["remember_ai_config"]

    render_app_header(current_user)

    if "extraction" not in st.session_state:
        st.session_state.extraction = blank_extraction()
    if "uploaded_path" not in st.session_state:
        st.session_state.uploaded_path = None
    if "uploaded_original_name" not in st.session_state:
        st.session_state.uploaded_original_name = ""
    if "uploaded_signature" not in st.session_state:
        st.session_state.uploaded_signature = ""
    ensure_entry_form_defaults()

    dashboard_tab, entry_tab, manage_tab, template_tab, settings_tab = st.tabs(
        ["Dashboard", "Nhap Ho So", "Quan Ly Ho So", "Templates", "Cau Hinh"]
    )

    with dashboard_tab:
        dashboard_view.render(sqlite_db_path)

    with entry_tab:
        entry_view.render(
            sqlite_db_path=sqlite_db_path,
            excel_template_path=excel_template_path,
            excel_dropdown_options=excel_dropdown_options,
            ai_provider=ai_provider,
            api_key=api_key,
            model=model,
            api_key_label=api_key_label,
            remember_ai_config=remember_current_ai_config,
        )

    with manage_tab:
        cases_view.render(
            sqlite_db_path,
            records_db_path,
            individual_template_dir,
            organization_template_dir,
        )

    with template_tab:
        templates_view.render(
            TEMPLATE_CONFIG_PATH,
            template_config,
            TEMPLATE_HISTORY_PATH,
        )

    with settings_tab:
        settings_view.render(
            TEMPLATE_CONFIG_PATH,
            template_config,
        )


if __name__ == "__main__":
    main()
