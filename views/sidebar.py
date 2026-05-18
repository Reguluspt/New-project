from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.app_config import AI_CONFIG_PATH, SQLITE_DATABASE, save_ai_config
from src.sqlite_store import import_excel_database, init_db, list_importable_excel_sheets


def render(
    *,
    ai_config: dict[str, object],
    excel_template_path: Path,
    individual_template_dir: Path,
    organization_template_dir: Path,
) -> dict[str, object]:
    with st.sidebar:
        st.header("Cấu hình AI quét GCN")
        ai_provider_options = ["Gemini", "OpenAI"]
        saved_ai_provider = str(ai_config.get("provider") or "Gemini")
        ai_provider = st.selectbox(
            "Nhà cung cấp AI",
            ai_provider_options,
            index=ai_provider_options.index(saved_ai_provider) if saved_ai_provider in ai_provider_options else 0,
        )
        saved_provider_config = dict(dict(ai_config.get("providers", {})).get(ai_provider, {}))
        if ai_provider == "Gemini":
            api_key_label = "GEMINI_API_KEY"
            api_key_default = os.getenv("GEMINI_API_KEY", "") or str(saved_provider_config.get("api_key") or "")
            model_default = os.getenv("GEMINI_MODEL", "") or str(saved_provider_config.get("model") or "gemini-2.5-flash")
        else:
            api_key_label = "OPENAI_API_KEY"
            api_key_default = os.getenv("OPENAI_API_KEY", "") or str(saved_provider_config.get("api_key") or "")
            model_default = os.getenv("OPENAI_MODEL", "") or str(saved_provider_config.get("model") or "gpt-4.1-mini")

        api_key = st.text_input(
            api_key_label,
            value=api_key_default,
            type="password",
            key=f"ai_api_key_{ai_provider}",
            help=f"File GCN sẽ được gửi đến {ai_provider} để đọc dữ liệu khi bấm nút quét.",
        )
        model = st.text_input("Model", value=model_default, key=f"ai_model_{ai_provider}")
        remember_api_key = st.checkbox(
            "Ghi nhớ API key trên máy này",
            value=True,
            help=f"Lưu vào {AI_CONFIG_PATH}. File này nằm trên máy hiện tại, không gửi lên máy chủ khác.",
        )
        ai_config_cols = st.columns(2)
        with ai_config_cols[0]:
            if st.button("Lưu cấu hình AI", width="stretch"):
                save_ai_config(
                    AI_CONFIG_PATH,
                    ai_config,
                    provider=ai_provider,
                    api_key=api_key,
                    model=model,
                    save_api_key=remember_api_key,
                )
                st.success("Đã lưu cấu hình AI.")
                st.rerun()
        with ai_config_cols[1]:
            if st.button("Xóa API key đã lưu", width="stretch"):
                save_ai_config(
                    AI_CONFIG_PATH,
                    ai_config,
                    provider=ai_provider,
                    api_key="",
                    model=model,
                    save_api_key=False,
                )
                st.success("Đã xóa API key đã lưu.")
                st.rerun()

        raw_db_path = st.text_input("File cơ sở dữ liệu SQLite", value=str(SQLITE_DATABASE))
        if ":" in raw_db_path and os.name == "posix":
            sqlite_db_path = SQLITE_DATABASE
        else:
            sqlite_db_path = Path(raw_db_path)
        init_db(sqlite_db_path)
        st.caption(f"Form Excel: {excel_template_path}")
        st.caption(f"Mẫu Word cá nhân: {individual_template_dir}")
        st.caption(f"Mẫu Word tổ chức: {organization_template_dir}")

        st.header("Import dữ liệu cũ")
        import_excel_path = st.text_input(
            "File Excel cần import",
            value=r"C:\Users\Truon\OneDrive\Desktop\Nháp\Theo doi hs.xlsm",
        )
        import_sheet = st.text_input("Tên sheet cụ thể (để trống = import toàn bộ sheet dữ liệu)", value="")
        importable_sheet_names: list[str] = []
        import_path = Path(import_excel_path)
        if import_path.exists():
            try:
                importable_sheet_names = list_importable_excel_sheets(import_path)
            except Exception as exc:
                st.caption(f"Không đọc được danh sách sheet: {exc}")
        if importable_sheet_names:
            st.caption("Sheet dữ liệu nhận diện được: " + ", ".join(importable_sheet_names))
        if st.button("Import Excel vào SQLite", width="stretch"):
            try:
                imported = import_excel_database(
                    sqlite_db_path,
                    import_path,
                    sheet_name=import_sheet.strip() or None,
                )
                mode_text = f"sheet {import_sheet.strip()}" if import_sheet.strip() else "toàn bộ sheet dữ liệu"
                st.success(f"Đã import {imported} hồ sơ từ {mode_text} vào SQLite.")
            except Exception as exc:
                st.error(f"Import thất bại: {exc}")
        st.caption("AI online hỗ trợ đọc PDF scan/ảnh GCN. Luôn kiểm tra lại trước khi xuất hồ sơ.")

    def remember_current_ai_config() -> None:
        if not remember_api_key:
            return
        save_ai_config(
            AI_CONFIG_PATH,
            ai_config,
            provider=ai_provider,
            api_key=api_key,
            model=model,
            save_api_key=True,
        )

    return {
        "sqlite_db_path": sqlite_db_path,
        "ai_provider": ai_provider,
        "api_key": api_key,
        "model": model,
        "api_key_label": api_key_label,
        "remember_ai_config": remember_current_ai_config,
    }
