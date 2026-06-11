from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.app_config import ROOT
from src.contracts import short_contract_number
from src.database_manager import load_record_candidates
from src.record_case_sync import sync_records_to_cases
from src.sqlite_store import get_case
from views import case_documents, case_revenue, case_table





def _web_error_dir() -> Path:
    return ROOT / "logs" / "errors"


def _web_error_files(error_dir: Path, record_filter: str = "") -> list[Path]:
    if not error_dir.exists():
        return []

    record_filter = record_filter.strip().lstrip("#")
    files = [
        path
        for path in error_dir.iterdir()
        if path.is_file()
        and path.name.startswith("error_web_entry_")
        and path.suffix.lower() in {".png", ".html"}
    ]
    if record_filter:
        needle = f"error_web_entry_{record_filter}"
        files = [path for path in files if path.name.startswith(needle)]

    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def _render_web_error_artifacts() -> None:
    error_dir = _web_error_dir()

    with st.expander("Ảnh lỗi nhập Web", expanded=False):
        st.caption(f"Thư mục lỗi: {error_dir}")
        col_filter, col_limit = st.columns([0.72, 0.28])
        with col_filter:
            record_filter = st.text_input(
                "Lọc theo mã hồ sơ",
                placeholder="Ví dụ: 2274",
                key="web_error_record_filter",
            )
        with col_limit:
            limit = st.number_input(
                "Số file hiển thị",
                min_value=3,
                max_value=50,
                value=6,
                step=3,
                key="web_error_file_limit",
            )

        files = _web_error_files(error_dir, record_filter)
        if not files:
            st.info("Chưa tìm thấy ảnh hoặc HTML lỗi nhập Web phù hợp.")
            return

        shown_files = files[: int(limit)]
        st.caption(f"Tìm thấy {len(files)} file, đang hiển thị {len(shown_files)} file mới nhất.")
        for path in shown_files:
            modified_text = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            st.markdown(f"**{path.name}** · {modified_text}")
            if path.suffix.lower() == ".png":
                if st.checkbox("Xem ảnh", key=f"preview_web_error_{path.name}"):
                    st.image(str(path), use_container_width=True)
                label = "Tải ảnh lỗi"
                mime = "image/png"
            else:
                label = "Tải HTML lỗi"
                mime = "text/html"

            st.download_button(
                label,
                data=path.read_bytes(),
                file_name=path.name,
                mime=mime,
                key=f"download_web_error_{path.name}",
            )


def render(
    db_path: Path,
    records_db_path: Path,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
    st.markdown(
        """
        <style>
            .block-container {
                max-width: none !important;
                width: 100% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    tab_cases, tab_revenue = st.tabs(["📋 Danh mục hồ sơ", "📊 Doanh thu & Công nợ"])

    with tab_cases:
        try:
            # Only sync once per session or if manually requested to avoid slow UI
            if "last_sync_done" not in st.session_state:
                st.session_state["last_sync_done"] = True # Set first to prevent retry on failure
                synced_count = asyncio.run(sync_records_to_cases(records_db_path, db_path, limit=1000))
            else:
                synced_count = 0
            records = asyncio.run(load_record_candidates(records_db_path, limit=30))
        except Exception as exc:
            records = []
            synced_count = 0
            st.warning(f"Không đọc được bảng records từ Telegram/Mail: {exc}")

        quick_action = st.session_state.pop("quick_action", None)
        if quick_action and isinstance(quick_action, dict):
            target_id = int(quick_action["case_id"])
            target_case = get_case(db_path, target_id)
            case_documents.handle_quick_action(
                quick_action,
                selected_id=target_id,
                refreshed_case=target_case,
                individual_templates_dir=individual_templates_dir,
                organization_templates_dir=organization_templates_dir,
                db_path=db_path,
            )

        selected_case = case_table.render(
            db_path,
            records_db_path,
            individual_templates_dir=individual_templates_dir,
            organization_templates_dir=organization_templates_dir,
        )

        # Move the Telegram / Mail expander here to the bottom of the page
        with st.expander("Hồ sơ từ Telegram / Mail Listener", expanded=False):
            exp_col1, exp_col2 = st.columns([0.8, 0.2])
            with exp_col1:
                st.caption(f"Nguồn dữ liệu trực tiếp: {records_db_path}")
            with exp_col2:
                if st.button("Làm mới 🔄", key="force_sync_records", width="stretch"):
                    synced_count = asyncio.run(sync_records_to_cases(records_db_path, db_path, limit=1000))
                    records = asyncio.run(load_record_candidates(records_db_path, limit=30))
                    st.toast(f"Đã đồng bộ {synced_count} hồ sơ mới!")
                    st.rerun()
            if synced_count:
                st.caption(f"Đã đồng bộ {synced_count} hồ sơ từ records sang danh mục chính.")
            if records:
                st.dataframe(
                    [
                        {
                            "ID": record.get("id", ""),
                            "Trạng thái": record.get("status", ""),
                            "Số HĐ": short_contract_number(record.get("contract_number"), fallback=""),
                            "Khách hàng": record.get("customer_info") or record.get("chu_so_huu") or "",
                            "Tài sản": record.get("asset_description") or record.get("asset_type") or "",
                            "Địa chỉ": record.get("dia_chi", ""),
                            "Số CT": record.get("certificate_number", ""),
                            "Tạo lúc": record.get("created_at", ""),
                        }
                        for record in records
                    ],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("Chưa có hồ sơ nào trong bảng records.")

        _render_web_error_artifacts()

    with tab_revenue:
        case_revenue.render(db_path)

