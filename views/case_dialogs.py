from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from src.app_config import SAMPLE_TEMPLATE, UNPAID_STATUS
from src.app_config import options_with_current
from src.database_manager import get_db_path
from src.excel_writer import load_dropdown_options
from src.record_case_sync import sync_case_delete_to_record, sync_case_to_record
from src.sqlite_store import (
    CANCELED_CASE_STATUS,
    DEFAULT_CASE_STATUS,
    DEFAULT_PAYMENT_STATUS,
    delete_case,
    distinct_case_values,
    get_all_organizations,
    get_case,
    update_case,
)


DEFAULT_ASSET_TYPE_OPTIONS = ["BĐS đặc thù khác", "Máy móc thiết bị"]
DEFAULT_VALUATION_PURPOSE_OPTIONS = [
    "Làm cơ sở tham khảo để vay vốn",
    "Làm cơ sở tham khảo để xử lý tài sản bảo đảm",
]


def _organization_options(organizations: list[dict[str, object]]) -> list[tuple[str, dict[str, object]]]:
    options: list[tuple[str, dict[str, object]]] = []
    seen: set[str] = set()
    for org in organizations:
        name = str(org.get("name") or "").strip()
        if not name:
            continue
        tax_code = str(org.get("tax_code") or "").strip()
        unique_key = f"{tax_code.casefold()}|{name.casefold()}"
        if unique_key in seen:
            continue
        seen.add(unique_key)
        label = f"{name} ({tax_code})" if tax_code else name
        options.append((label, org))
    return options


def _valid_valuation_purpose(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    digits = sum(ch.isdigit() for ch in text)
    letters = sum(ch.isalpha() for ch in text)
    if letters < 8:
        return False
    if digits > letters:
        return False
    return True


def _purpose_options(current_value: str) -> list[str]:
    try:
        excel_options = load_dropdown_options(SAMPLE_TEMPLATE).get("valuation_purpose", [])
    except Exception:
        excel_options = []
    options: list[str] = []
    seen: set[str] = set()
    for value in [current_value, *DEFAULT_VALUATION_PURPOSE_OPTIONS, *excel_options]:
        text = str(value or "").strip()
        key = text.casefold()
        if key in seen or not _valid_valuation_purpose(text):
            continue
        seen.add(key)
        options.append(text)
    return options or [""]


def _format_date_input(key: str) -> None:
    val = str(st.session_state.get(key) or "").strip()
    if val.isdigit():
        if len(val) == 8:
            st.session_state[key] = f"{val[:2]}/{val[2:4]}/{val[4:]}"
        elif len(val) == 6:
            st.session_state[key] = f"{val[:2]}/{val[2:4]}/20{val[4:]}"


@st.dialog("Sửa hồ sơ", width="large")
def open_case_edit_dialog(db_path: Path, case_id: int) -> None:
    case = get_case(db_path, case_id)
    if not case:
        st.error("Không tìm thấy hồ sơ.")
        return

    suffix = f"dialog_{case_id}"
    organizations = get_all_organizations(db_path)
    organization_options = _organization_options(organizations)
    current_org_name = str(case.get("customer_info") or "").strip()
    current_tax_code = str(case.get("tax_code") or "").strip()
    customer_info_org = ""
    customer_address_org = ""
    tax_code = ""
    representative_name = ""
    representative_position = ""
    selected_org_index = 0
    for index, (_label, org) in enumerate(organization_options):
        if (
            current_tax_code
            and str(org.get("tax_code") or "").strip().casefold() == current_tax_code.casefold()
        ) or (
            current_org_name
            and str(org.get("name") or "").strip().casefold() == current_org_name.casefold()
        ):
            selected_org_index = index
            break

    organization_source = "Nhập thủ công"
    selected_organization = None

    try:
        asset_type_options = distinct_case_values(db_path, "asset_type")
    except Exception:
        asset_type_options = []
    asset_type_options = options_with_current(
        [*DEFAULT_ASSET_TYPE_OPTIONS, *asset_type_options],
        str(case.get("asset_type") or "").strip(),
    )
    valuation_purpose_options = _purpose_options(str(case.get("valuation_purpose") or "").strip())

    with st.container():
        st.subheader("Thông tin hợp đồng & chứng thư")
        col_contract1, col_contract2, col_contract3 = st.columns(3)
        with col_contract1:
            contract_number = st.text_input("Số hợp đồng", value=case.get("contract_number") or "", key=f"edit_contract_{suffix}")
        with col_contract2:
            contract_date = st.text_input(
                "Ngày hợp đồng",
                value=case.get("contract_date") or "",
                placeholder="dd/mm/yyyy",
                key=f"edit_contract_date_{suffix}",
                on_change=_format_date_input,
                args=(f"edit_contract_date_{suffix}",)
            )
        with col_contract3:
            certificate_date = st.text_input(
                "Ngày chứng thư",
                value=case.get("certificate_date") or "",
                placeholder="dd/mm/yyyy",
                key=f"edit_certificate_date_{suffix}",
                on_change=_format_date_input,
                args=(f"edit_certificate_date_{suffix}",)
            )

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
            organization_source = st.radio(
                "Nguồn thông tin công ty",
                ["Nhập thủ công", "Chọn từ danh sách đã lưu"],
                horizontal=True,
                index=1 if organization_options else 0,
                key=f"edit_org_source_{suffix}",
            )
            selected_organization = None
            if organization_source == "Chọn từ danh sách đã lưu" and organization_options:
                selected_org_label = st.selectbox(
                    "Tên công ty / tổ chức",
                    [label for label, _org in organization_options],
                    index=selected_org_index,
                    key=f"edit_customer_org_select_{suffix}",
                )
                selected_organization = next(
                    org for label, org in organization_options if label == selected_org_label
                )
            elif organization_source == "Chọn từ danh sách đã lưu":
                st.info("Chưa có công ty nào trong Danh bạ Tổ Chức.")

            if selected_organization:
                customer_info_org = str(selected_organization.get("name") or "").strip()
                customer_address_org = str(selected_organization.get("address") or "").strip()
                tax_code = str(selected_organization.get("tax_code") or "").strip()
                representative_name = str(selected_organization.get("representative") or "").strip()
                representative_position = str(selected_organization.get("position") or "").strip()
                st.text_input("Tên công ty / tổ chức", value=customer_info_org, disabled=True, key=f"edit_customer_org_selected_{suffix}_{selected_organization.get('id', '')}")
            else:
                customer_info_org = st.text_input("Tên công ty / tổ chức", value=case.get("customer_info") or "" if is_org_db else "", key=f"edit_customer_org_{suffix}")
                customer_address_org = str(case.get("customer_address") or "" if is_org_db else "")
                tax_code = str(case.get("tax_code") or "")
                representative_name = str(case.get("representative_name") or "")
                representative_position = str(case.get("representative_position") or "")

            customer_address_org = st.text_input("Địa chỉ công ty", value=customer_address_org, disabled=bool(selected_organization), key=f"edit_address_org_{suffix}_{selected_organization.get('id', '') if selected_organization else 'manual'}")
            tax_code = st.text_input("Mã số thuế", value=tax_code, disabled=bool(selected_organization), key=f"edit_tax_{suffix}_{selected_organization.get('id', '') if selected_organization else 'manual'}")
            representative_name = st.text_input("Người đại diện", value=representative_name, disabled=bool(selected_organization), key=f"edit_representative_{suffix}_{selected_organization.get('id', '') if selected_organization else 'manual'}")
            representative_position = st.text_input("Chức vụ người đại diện", value=representative_position, disabled=bool(selected_organization), key=f"edit_representative_position_{suffix}_{selected_organization.get('id', '') if selected_organization else 'manual'}")

            with st.expander("Thông tin nhận bàn giao & ủy quyền đại diện (Ẩn/Hiện)", expanded=False):
                handover_contact_name = st.text_input("Người nhận bàn giao", value=case.get("handover_contact_name") or "", key=f"edit_handover_name_{suffix}")
                handover_contact_position = st.text_input("Chức vụ người nhận bàn giao", value=case.get("handover_contact_position") or "", key=f"edit_handover_position_{suffix}")
                handover_contact_phone = st.text_input("Điện thoại người nhận bàn giao", value=case.get("handover_contact_phone") or "", key=f"edit_handover_phone_{suffix}")
                authorization_note = st.text_area("Căn cứ/giấy ủy quyền đại diện", value=case.get("authorization_note") or "", height=70, key=f"edit_authorization_{suffix}")

        st.subheader("Thông tin Tài sản")
        col_ts1, col_ts2 = st.columns(2)
        with col_ts1:
            asset_type = st.selectbox(
                "Loại tài sản",
                asset_type_options,
                index=0,
                key=f"edit_asset_type_{suffix}",
            )
            valuation_purpose = st.selectbox(
                "Mục đích thẩm định",
                valuation_purpose_options,
                index=0,
                key=f"edit_purpose_{suffix}",
            )
            
            # Chi nhánh thẩm định và Chọn văn phòng
            branch_options = ["cn Đà Nẵng", "cn Miền Bắc", "CN Miền Nam"]
            office_mapping = {
                "cn Đà Nẵng": ["vp Đà Nẵng"],
                "cn Miền Bắc": ["vp Hưng Yên", "vp Hải Phòng", "vp Hà Nam Ninh", "vp Hà Nội", "vp Nghệ An", "vp Thái Nguyên"],
                "CN Miền Nam": ["vp Cần Thơ", "vp HCM", "vp Đồng Nai", "vp Bình Dương"]
            }
            db_branch = str(case.get("valuation_branch") or "cn Đà Nẵng").strip()
            db_office = str(case.get("office") or "vp Đà Nẵng").strip()
            if db_branch not in branch_options:
                db_branch = "cn Đà Nẵng"
            branch_index = branch_options.index(db_branch)
            valuation_branch = st.selectbox(
                "Chi nhánh thẩm định",
                branch_options,
                index=branch_index,
                key=f"edit_valuation_branch_{suffix}"
            )
            current_offices = office_mapping.get(valuation_branch, ["vp Đà Nẵng"])
            if db_office in current_offices:
                office_index = current_offices.index(db_office)
            else:
                office_index = 0
            office = st.selectbox(
                "Chọn Văn Phòng",
                current_offices,
                index=office_index,
                key=f"edit_office_{valuation_branch}_{suffix}"
            )
        with col_ts2:
            asset_description = st.text_area(
                "Tài sản thẩm định giá",
                value=case.get("asset_description") or "",
                height=110,
                key=f"edit_asset_{suffix}",
                placeholder="Vd: Thửa đất số ...., tờ bản đồ số ....; tại địa chỉ....."
            )

        st.subheader("Thông tin Nghiệp vụ")
        col_nv1, col_nv2 = st.columns(2)
        with col_nv1:
            case_status = st.selectbox("Trạng thái hồ sơ", [DEFAULT_CASE_STATUS, "Hoàn thành", CANCELED_CASE_STATUS], index=[DEFAULT_CASE_STATUS, "Hoàn thành", CANCELED_CASE_STATUS].index(case.get("case_status") or DEFAULT_CASE_STATUS), key=f"edit_case_status_{suffix}")
            execution_month = st.text_input("Tháng thực hiện", value=case.get("execution_month") or "", key=f"edit_execution_month_{suffix}")
            source = st.text_input("Nguồn/ngân hàng", value=case.get("source") or "", key=f"edit_source_{suffix}")
            preliminary_status = st.text_input("Sơ bộ", value=case.get("preliminary_status") or "", key=f"edit_preliminary_{suffix}")
        with col_nv2:
            payment_status = st.selectbox("Trạng thái thanh toán", [DEFAULT_PAYMENT_STATUS, UNPAID_STATUS], index=0 if (case.get("payment_status") or DEFAULT_PAYMENT_STATUS) == DEFAULT_PAYMENT_STATUS else 1, key=f"edit_payment_status_{suffix}")
            valuation_fee_number = st.text_input("Phí thẩm định", value=str(case.get("valuation_fee_number") or ""), key=f"edit_fee_{suffix}")
            advance_payment = st.text_input("Tạm ứng", value=case.get("advance_payment") or "", key=f"edit_advance_{suffix}")

        personal_note = st.text_area("Ghi chú cá nhân", value=case.get("personal_note") or "", height=70, key=f"edit_note_{suffix}")
        confirm_delete = st.checkbox("Tôi xác nhận muốn xóa hồ sơ này", key=f"confirm_delete_{suffix}")

        action_cols = st.columns(3)
        with action_cols[0]:
            update_clicked = st.button("Cập nhật hồ sơ", type="primary", width="stretch", key=f"btn_update_{suffix}")
        with action_cols[1]:
            delete_clicked = st.button("Xóa hồ sơ", width="stretch", key=f"btn_delete_{suffix}")
        with action_cols[2]:
            quick_export_clicked = st.button("Xuất nhanh hồ sơ", width="stretch", key=f"btn_quick_export_{suffix}")

    from src.sqlite_store import format_contract_number
    edited_values = {
        "customer_type": "organization" if is_org else "individual",
        "case_status": case_status,
        "cancel_reason": "",
        "execution_month": execution_month,
        "payment_status": payment_status,
        "contract_number": format_contract_number(contract_number),
        "contract_date": contract_date,
        "certificate_date": certificate_date,
        "customer_info": customer_info_org if is_org else customer_info_ind,
        "customer_address": customer_address_org if is_org else customer_address_ind,
        "customer_phone": handover_contact_phone if is_org else customer_phone_ind,
        "citizen_id": "" if is_org else citizen_id_ind,
        "source": source,
        "valuation_fee_number": valuation_fee_number,
        "preliminary_status": preliminary_status,
        "so_thua_dat": case.get("so_thua_dat") or "",
        "so_to_ban_do": case.get("so_to_ban_do") or "",
        "dia_chi_thua_dat": case.get("dia_chi_thua_dat") or "",
        "owner_name": case.get("owner_name") or "",
        "asset_type": asset_type,
        "expected_finish_date": case.get("expected_finish_date") or "",
        "advance_payment": advance_payment,
        "asset_description": asset_description,
        "valuation_purpose": valuation_purpose,
        "valuation_branch": valuation_branch,
        "office": office,
        "personal_note": personal_note,
        "survey_cost": case.get("survey_cost") or "",
        "business_staff": case.get("business_staff") or "",
        "valuation_staff": case.get("valuation_staff") or "",
        "controller": case.get("controller") or "",
        "legal_note": case.get("legal_note") or "",
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
