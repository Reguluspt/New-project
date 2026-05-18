from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from src.contracts import short_contract_number
from src.database_manager import load_record_candidates
from src.record_case_sync import sync_records_to_cases
from src.sqlite_store import get_case
from views import case_documents, case_revenue, case_table





def render(
    db_path: Path,
    records_db_path: Path,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
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
                if st.button("Làm mới 🔄", key="force_sync_records", use_container_width=True):
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

    with tab_revenue:
        case_revenue.render(db_path)

