from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from src.app_config import UNPAID_STATUS
from src.database_manager import get_db_path
from src.record_case_sync import sync_case_delete_to_record, sync_case_to_record
from src.sqlite_store import (
    CANCELED_CASE_STATUS,
    DEFAULT_CASE_STATUS,
    DEFAULT_PAYMENT_STATUS,
    delete_case,
    get_case,
    update_case,
)


@st.dialog("Sửa hồ sơ", width="large")
def open_case_edit_dialog(db_path: Path, case_id: int) -> None:
    case = get_case(db_path, case_id)
    if not case:
        st.error("Không tìm thấy hồ sơ.")
        return

    suffix = f"dialog_{case_id}"
    with st.form(f"edit_case_dialog_{suffix}"):
        st.subheader("Thông tin khách hàng")
        is_org_db = case.get("customer_type") == "organization"
        customer_type_choice = st.radio(
            "Loại khách hàng",
            ["🧑 Cá nhân", "🏢 Tổ chức"],
            index=1 if is_org_db else 0,
            horizontal=True,
            key=f"edit_type_choice_{suffix}",
            help="Chuyển đổi giữa Cá nhân và Tổ chức sẽ thay đổi cách lấy thông tin Tên và Địa chỉ khi lưu."
        )
        is_org = "Tổ chức" in customer_type_choice

        tab_ca_nhan, tab_to_chuc = st.tabs(["🧑 Chi tiết Cá nhân", "🏢 Chi tiết Tổ chức"])
        
        with tab_ca_nhan:
            customer_info_ind = st.text_input("Tên khách hàng", value=case.get("customer_info") or "" if not is_org_db else "", key=f"edit_customer_ind_{suffix}")
            edit_ind_col1, edit_ind_col2, edit_ind_col3 = st.columns(3)
            with edit_ind_col1:
                customer_address_ind = st.text_input("Địa chỉ khách hàng", value=case.get("customer_address") or "" if not is_org_db else "", key=f"edit_address_ind_{suffix}")
            with edit_ind_col2:
                citizen_id_ind = st.text_input("Số CCCD/CMND", value=case.get("citizen_id") or "" if not is_org_db else "", key=f"edit_citizen_ind_{suffix}")
            with edit_ind_col3:
                customer_phone_ind = st.text_input("Số điện thoại", value=case.get("customer_phone") or "" if not is_org_db else "", key=f"edit_phone_ind_{suffix}")
            
        with tab_to_chuc:
            customer_info_org = st.text_input("Tên công ty / tổ chức", value=case.get("customer_info") or "" if is_org_db else "", key=f"edit_customer_org_{suffix}")
            customer_address_org = st.text_input("Địa chỉ công ty", value=case.get("customer_address") or "" if is_org_db else "", key=f"edit_address_org_{suffix}")
            org_col1, org_col2 = st.columns(2)
            with org_col1:
                tax_code = st.text_input("Mã số thuế", value=case.get("tax_code") or "", key=f"edit_tax_{suffix}")
                representative_name = st.text_input("Người đại diện", value=case.get("representative_name") or "", key=f"edit_representative_{suffix}")
                representative_position = st.text_input("Chức vụ người đại diện", value=case.get("representative_position") or "", key=f"edit_representative_position_{suffix}")
            with org_col2:
                handover_contact_name = st.text_input("Người nhận bàn giao", value=case.get("handover_contact_name") or "", key=f"edit_handover_name_{suffix}")
                handover_contact_position = st.text_input("Chức vụ người nhận bàn giao", value=case.get("handover_contact_position") or "", key=f"edit_handover_position_{suffix}")
                handover_contact_phone = st.text_input("Điện thoại người nhận bàn giao", value=case.get("handover_contact_phone") or "", key=f"edit_handover_phone_{suffix}")
            authorization_note = st.text_area("Căn cứ/giấy ủy quyền đại diện", value=case.get("authorization_note") or "", height=70, key=f"edit_authorization_{suffix}")

        st.subheader("Thông tin Tài sản")
        col_ts1, col_ts2 = st.columns(2)
        with col_ts1:
            so_thua = st.text_area("Số thửa đất", value=case.get("so_thua_dat") or "", height=80, key=f"edit_so_thua_{suffix}")
            land_address = st.text_area("Địa chỉ thửa đất", value=case.get("dia_chi_thua_dat") or "", height=80, key=f"edit_land_address_{suffix}")
            owner_name = st.text_area("Chủ sở hữu cuối cùng", value=case.get("owner_name") or "", height=80, key=f"edit_owner_{suffix}")
        with col_ts2:
            so_to = st.text_area("Số tờ bản đồ", value=case.get("so_to_ban_do") or "", height=80, key=f"edit_so_to_{suffix}")
            asset_type = st.text_input("Loại tài sản", value=case.get("asset_type") or "", key=f"edit_asset_type_{suffix}")
            asset_description = st.text_area("Tài sản thẩm định giá", value=case.get("asset_description") or "", height=80, key=f"edit_asset_{suffix}")

        st.subheader("Thông tin Nghiệp vụ")
        col_nv1, col_nv2 = st.columns(2)
        with col_nv1:
            case_status = st.selectbox("Trạng thái hồ sơ", [DEFAULT_CASE_STATUS, "Hoàn thành", CANCELED_CASE_STATUS], index=[DEFAULT_CASE_STATUS, "Hoàn thành", CANCELED_CASE_STATUS].index(case.get("case_status") or DEFAULT_CASE_STATUS), key=f"edit_case_status_{suffix}")
            execution_month = st.text_input("Tháng thực hiện", value=case.get("execution_month") or "", key=f"edit_execution_month_{suffix}")
            contract_number = st.text_input("Số hợp đồng", value=case.get("contract_number") or "", key=f"edit_contract_{suffix}")
            contract_date = st.text_input("Ngày hợp đồng", value=case.get("contract_date") or "", placeholder="dd/mm/yyyy", key=f"edit_contract_date_{suffix}")
            certificate_date = st.text_input("Ngày chứng thư", value=case.get("certificate_date") or "", placeholder="dd/mm/yyyy", key=f"edit_certificate_date_{suffix}")
            source = st.text_input("Nguồn/ngân hàng", value=case.get("source") or "", key=f"edit_source_{suffix}")
            preliminary_status = st.text_input("Sơ bộ", value=case.get("preliminary_status") or "", key=f"edit_preliminary_{suffix}")
        with col_nv2:
            payment_status = st.selectbox("Trạng thái thanh toán", [DEFAULT_PAYMENT_STATUS, UNPAID_STATUS], index=0 if (case.get("payment_status") or DEFAULT_PAYMENT_STATUS) == DEFAULT_PAYMENT_STATUS else 1, key=f"edit_payment_status_{suffix}")
            valuation_fee_number = st.text_input("Phí thẩm định", value=str(case.get("valuation_fee_number") or ""), key=f"edit_fee_{suffix}")
            expected_finish_date = st.text_input("Thời gian dự kiến hoàn thành", value=case.get("expected_finish_date") or "", key=f"edit_finish_{suffix}")
            advance_payment = st.text_input("Tạm ứng", value=case.get("advance_payment") or "", key=f"edit_advance_{suffix}")

        valuation_purpose = st.text_area("Mục đích thẩm định", value=case.get("valuation_purpose") or "", height=70, key=f"edit_purpose_{suffix}")
        personal_note = st.text_area("Ghi chú cá nhân", value=case.get("personal_note") or "", height=70, key=f"edit_note_{suffix}")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            survey_cost = st.text_input("Chi phí khảo sát", value=case.get("survey_cost") or "", key=f"edit_survey_{suffix}")
        with col4:
            business_staff = st.text_input("Chuyên viên kinh doanh", value=case.get("business_staff") or "", key=f"edit_business_{suffix}")
        with col5:
            valuation_staff = st.text_input("Chuyên viên nghiệp vụ", value=case.get("valuation_staff") or "", key=f"edit_valuation_staff_{suffix}")

        controller = st.text_input("Kiểm soát", value=case.get("controller") or "", key=f"edit_controller_{suffix}")
        legal_note = st.text_input("Liên hệ khách hàng lấy pháp lý", value=case.get("legal_note") or "", key=f"edit_legal_{suffix}")
        confirm_delete = st.checkbox("Tôi xác nhận muốn xóa hồ sơ này", key=f"confirm_delete_{suffix}")

        action_cols = st.columns(3)
        with action_cols[0]:
            update_clicked = st.form_submit_button("Cập nhật hồ sơ", type="primary", width="stretch")
        with action_cols[1]:
            delete_clicked = st.form_submit_button("Xóa hồ sơ", width="stretch")
        with action_cols[2]:
            quick_export_clicked = st.form_submit_button("Xuất nhanh hồ sơ", width="stretch")

    edited_values = {
        "customer_type": "organization" if is_org else "individual",
        "case_status": case_status,
        "cancel_reason": "",
        "execution_month": execution_month,
        "payment_status": payment_status,
        "contract_number": contract_number,
        "contract_date": contract_date,
        "certificate_date": certificate_date,
        "customer_info": customer_info_org if is_org else customer_info_ind,
        "customer_address": customer_address_org if is_org else customer_address_ind,
        "customer_phone": handover_contact_phone if is_org else customer_phone_ind,
        "citizen_id": "" if is_org else citizen_id_ind,
        "source": source,
        "valuation_fee_number": valuation_fee_number,
        "preliminary_status": preliminary_status,
        "so_thua_dat": so_thua,
        "so_to_ban_do": so_to,
        "dia_chi_thua_dat": land_address,
        "owner_name": owner_name,
        "asset_type": asset_type,
        "expected_finish_date": expected_finish_date,
        "advance_payment": advance_payment,
        "asset_description": asset_description,
        "valuation_purpose": valuation_purpose,
        "personal_note": personal_note,
        "survey_cost": survey_cost,
        "business_staff": business_staff,
        "valuation_staff": valuation_staff,
        "controller": controller,
        "legal_note": legal_note,
        "tax_code": tax_code,
        "representative_name": representative_name,
        "representative_position": representative_position,
        "authorization_note": authorization_note,
        "handover_contact_name": handover_contact_name,
        "handover_contact_position": handover_contact_position,
        "handover_contact_phone": handover_contact_phone,
    }

    if update_clicked:
        update_case(db_path, case_id, edited_values)
        asyncio.run(sync_case_to_record(get_db_path(), db_path, case_id))
        st.session_state["active_case_id"] = case_id
        st.success(f"Đã cập nhật hồ sơ #{case_id}.")
        st.rerun()

    if quick_export_clicked:
        update_case(db_path, case_id, edited_values)
        asyncio.run(sync_case_to_record(get_db_path(), db_path, case_id))
        st.session_state["active_case_id"] = case_id
        st.session_state["case_documents_dialog_open"] = True
        st.rerun()

    if delete_clicked:
        if not confirm_delete:
            st.error("Cần tick xác nhận trước khi xóa.")
        else:
            asyncio.run(sync_case_delete_to_record(get_db_path(), db_path, case_id))
            delete_case(db_path, case_id)
            st.session_state.pop("active_case_id", None)
            st.success(f"Đã xóa hồ sơ #{case_id}.")
            st.rerun()
