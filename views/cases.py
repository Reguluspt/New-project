from __future__ import annotations

from pathlib import Path

import streamlit as st

from views import case_documents, case_table


@st.dialog("Xem và xuất hồ sơ", width="large", on_dismiss="rerun")
def _render_case_documents_dialog(
    *,
    selected_case: dict[str, object],
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
    case = dict(selected_case["case"])
    selected_id = int(selected_case["selected_id"])
    st.info(
        "Hồ sơ đang chọn: "
        f"#{selected_id} - {case.get('contract_number') or 'Chưa có số HĐ'} - {case.get('customer_info') or 'Chưa có khách hàng'}"
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
    )
    if st.button("Đóng", width="stretch"):
        st.session_state["case_documents_dialog_open"] = False
        st.rerun()


def render(
    db_path: Path,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
    selected_case = case_table.render(db_path)
    if not selected_case:
        return

    if st.session_state.get("case_documents_dialog_open"):
        _render_case_documents_dialog(
            selected_case=selected_case,
            individual_templates_dir=individual_templates_dir,
            organization_templates_dir=organization_templates_dir,
        )
