from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from src.contracts import short_contract_number
from src.database_manager import load_record_candidates
from src.record_case_sync import sync_records_to_cases
from views import case_documents, case_revenue, case_table


@st.dialog("Xem và xuất hồ sơ", width="large", on_dismiss="rerun")
def _render_case_documents_dialog(
    *,
    db_path: Path,
    selected_case: dict[str, object],
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
    case = dict(selected_case["case"])
    selected_id = int(selected_case["selected_id"])
    st.info(
        "Hồ sơ đang chọn: "
        f"#{selected_id} - {short_contract_number(case.get('contract_number'), fallback='Chưa có số HĐ')} - {case.get('customer_info') or 'Chưa có khách hàng'}"
    )
    case_documents.render(
        selected_id=selected_id,
        case=case,
        refreshed_case=(dict(selected_case["refreshed_case"]) if selected_case.get("refreshed_case") else None),
        effective_case_folder=(
            Path(str(selected_case["effective_case_folder"]))
            if selected_case.get("effective_case_folder")
            else None
        ),
        individual_templates_dir=individual_templates_dir,
        organization_templates_dir=organization_templates_dir,
        db_path=db_path,
    )
    if st.button("Đóng", width="stretch"):
        st.session_state["case_documents_dialog_open"] = False
        st.rerun()


def render(
    db_path: Path,
    records_db_path: Path,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
    tab_cases, tab_revenue = st.tabs(["📋 Danh mục hồ sơ", "📊 Doanh thu & Công nợ"])

    with tab_revenue:
        case_revenue.render(db_path)

    with tab_cases:
        try:
            synced_count = asyncio.run(sync_records_to_cases(records_db_path, db_path, limit=1000))
            records = asyncio.run(load_record_candidates(records_db_path, limit=30))
        except Exception as exc:
            records = []
            synced_count = 0
            st.warning(f"Khong doc duoc bang records tu Telegram/Mail: {exc}")

        with st.expander("Ho so tu Telegram / Mail Listener", expanded=True):
            st.caption(f"Nguon du lieu truc tiep, khong cache: {records_db_path}")
            if synced_count:
                st.caption(f"Da dong bo {synced_count} ho so tu records sang danh muc chinh.")
            if records:
                st.dataframe(
                    [
                        {
                            "ID": record.get("id", ""),
                            "Trang thai": record.get("status", ""),
                            "So HD": short_contract_number(record.get("contract_number"), fallback=""),
                            "Khach hang": record.get("customer_info") or record.get("chu_so_huu") or "",
                            "Tai san": record.get("asset_description") or record.get("asset_type") or "",
                            "Dia chi": record.get("dia_chi", ""),
                            "So CT": record.get("certificate_number", ""),
                            "Tao luc": record.get("created_at", ""),
                        }
                        for record in records
                    ],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("Chua co ho so nao trong bang records.")

        selected_case = case_table.render(db_path)
        if not selected_case:
            return

        if st.session_state.get("case_documents_dialog_open"):
            _render_case_documents_dialog(
                db_path=db_path,
                selected_case=selected_case,
                individual_templates_dir=individual_templates_dir,
                organization_templates_dir=organization_templates_dir,
            )

