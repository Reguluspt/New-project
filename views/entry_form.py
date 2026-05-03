from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.app_config import (
    CASE_FILES_DIR,
    OUTPUT_DIR,
    UNPAID_STATUS,
    selectbox_from_excel,
    sync_form_to_gcn_from_fields,
)
from src.case_files import case_folder, save_original_file
from src.database_store import format_money, parse_money
from src.database_manager import create_outbound_tracking_record, resolve_records_db_path
from src.excel_writer import fill_template
from src.mail_service import send_appraisal_email
from src.sqlite_store import DEFAULT_CASE_STATUS, create_case, display_cases, recent_cases, update_case


def _hidden_gcn_value(session_key: str, extracted_value) -> str:
    if session_key not in st.session_state:
        st.session_state[session_key] = str(extracted_value.value or "").strip()
    return str(st.session_state.get(session_key) or "").strip()


def _format_fee_input() -> None:
    key = "entry_valuation_fee_number"
    amount = parse_money(st.session_state.get(key))
    if amount is not None:
        st.session_state[key] = format_money(amount)


async def _tracked_entry_mail_payload(output_values: dict[str, object]) -> dict[str, object]:
    records_db_path = Path(resolve_records_db_path())
    record_id = await create_outbound_tracking_record(records_db_path, output_values, file_path="desktop_entry")
    return {**output_values, "record_id": record_id, "records_db_path": str(records_db_path)}


def _send_entry_mail(output_values: dict[str, object]) -> None:
    mail_payload = asyncio.run(_tracked_entry_mail_payload(output_values))
    result = asyncio.run(send_appraisal_email(mail_payload))
    st.success(f"Đã gửi mail yêu cầu định giá tới {result.to_email}.")
    if result.cc_emails:
        st.caption(f"CC: {', '.join(result.cc_emails)}")


def render(
    *,
    sqlite_db_path: Path,
    excel_template_path: Path,
    excel_dropdown_options: dict,
) -> None:
    st.subheader("Bước 1 - Kiểm tra và xuất form nhập liệu")
    extraction = st.session_state.extraction

    so_thua = _hidden_gcn_value("so_thua", extraction.so_thua_dat)
    so_to = _hidden_gcn_value("so_to", extraction.so_to_ban_do)
    land_address = _hidden_gcn_value("land_address", extraction.dia_chi_thua_dat)
    owner_name = _hidden_gcn_value("owner_name", extraction.ten_chu_so_huu_cuoi_cung)
    owner_address = _hidden_gcn_value("owner_address", extraction.dia_chi_chu_so_huu_cuoi_cung)
    citizen_id = _hidden_gcn_value("citizen_id", extraction.so_cccd_chu_so_huu_cuoi_cung)

    execution_month = datetime.now().strftime("%m/%Y")
    case_status = DEFAULT_CASE_STATUS
    payment_status = UNPAID_STATUS

    with st.expander("Thông tin bổ sung cho form Excel", expanded=True):
        customer_type = st.selectbox(
            "Loại khách hàng",
            ["individual", "organization"],
            format_func=lambda value: "Cá nhân" if value == "individual" else "Tổ chức",
            key="entry_customer_type",
        )
        contract_number = st.text_input("Số hợp đồng", key="entry_contract_number")
        asset_type = selectbox_from_excel("Loại tài sản", "asset_type", excel_dropdown_options, "entry_asset_type")
        asset_description = st.text_area(
            "Tài sản thẩm định giá",
            height=88,
            key="entry_asset_description",
            on_change=sync_form_to_gcn_from_fields,
        )
        preliminary_status = selectbox_from_excel("Sơ bộ", "preliminary_status", excel_dropdown_options, "entry_preliminary_status")
        valuation_purpose = selectbox_from_excel("Mục đích thẩm định", "valuation_purpose", excel_dropdown_options, "entry_valuation_purpose")
        source = selectbox_from_excel("Nguồn/đối tác", "source", excel_dropdown_options, "entry_source")
        customer_info = st.text_input("Tên khách hàng", key="entry_customer_info", on_change=sync_form_to_gcn_from_fields)
        customer_address = st.text_input("Địa chỉ khách hàng", key="entry_customer_address", on_change=sync_form_to_gcn_from_fields)
        customer_citizen_id = st.text_input("Số CCCD/CMND", key="entry_citizen_id", on_change=sync_form_to_gcn_from_fields)
        valuation_fee_number = st.text_input("Phí thẩm định", key="entry_valuation_fee_number", on_change=_format_fee_input)
        advance_payment = st.text_input("Tạm ứng", key="entry_advance_payment")
        valuation_staff = selectbox_from_excel("Chuyên viên nghiệp vụ", "valuation_staff", excel_dropdown_options, "entry_valuation_staff")
        personal_note = st.text_area("Ghi chú cá nhân", height=68, key="entry_personal_note")
        with st.expander("Thông tin riêng cho khách hàng tổ chức", expanded=customer_type == "organization"):
            org_col1, org_col2 = st.columns(2)
            with org_col1:
                tax_code = st.text_input("Mã số thuế", key="entry_tax_code")
                representative_name = st.text_input("Người đại diện", key="entry_representative_name")
                representative_position = st.text_input("Chức vụ người đại diện", key="entry_representative_position")
            with org_col2:
                handover_contact_name = st.text_input("Người nhận bàn giao", key="entry_handover_contact_name")
                handover_contact_position = st.text_input("Chức vụ người nhận bàn giao", key="entry_handover_contact_position")
                handover_contact_phone = st.text_input("Điện thoại người nhận bàn giao", key="entry_handover_contact_phone")
            authorization_note = st.text_area("Căn cứ/giấy ủy quyền đại diện", height=70, key="entry_authorization_note")

    output_values = {
        "customer_type": customer_type,
        "case_status": case_status,
        "execution_month": execution_month,
        "payment_status": payment_status,
        "contract_number": contract_number,
        "asset_type": asset_type,
        "asset_description": asset_description,
        "preliminary_status": preliminary_status,
        "valuation_purpose": valuation_purpose,
        "source": source,
        "customer_info": customer_info,
        "customer_address": customer_address,
        "citizen_id": customer_citizen_id,
        "valuation_fee_number": valuation_fee_number,
        "advance_payment": advance_payment,
        "valuation_staff": valuation_staff,
        "personal_note": personal_note,
        "so_thua_dat": so_thua,
        "so_to_ban_do": so_to,
        "dia_chi_thua_dat": land_address,
        "owner_name": owner_name,
        "owner_address": owner_address,
        "owner_citizen_id": citizen_id,
        "tax_code": tax_code,
        "representative_name": representative_name,
        "representative_position": representative_position,
        "authorization_note": authorization_note,
        "handover_contact_name": handover_contact_name,
        "handover_contact_position": handover_contact_position,
        "handover_contact_phone": handover_contact_phone,
    }

    save_col, export_col, mail_col = st.columns(3)
    with save_col:
        if st.button("Lưu hồ sơ vào SQLite", width="stretch"):
            try:
                case_id = create_case(sqlite_db_path, output_values)
                folder = case_folder(
                    CASE_FILES_DIR,
                    case_id=case_id,
                    contract_number=contract_number,
                    customer_name=customer_info,
                )
                saved_original = save_original_file(
                    st.session_state.uploaded_path,
                    st.session_state.uploaded_original_name,
                    folder,
                )
                update_case(
                    sqlite_db_path,
                    case_id,
                    {
                        **output_values,
                        "case_folder": str(folder),
                        "original_file_path": str(saved_original) if saved_original else "",
                    },
                )
                st.success(f"Đã lưu hồ sơ #{case_id} vào SQLite.")
            except Exception as exc:
                st.error(f"Lưu SQLite thất bại: {exc}")

    with export_col:
        export_clicked = st.button("Xuất ra Form nhập liệu Excel", type="primary", width="stretch")

    with mail_col:
        mail_clicked = st.button("Gửi mail yêu cầu định giá", width="stretch", icon=":material/mail:")

    if mail_clicked:
        try:
            _send_entry_mail(output_values)
        except Exception as exc:
            st.error(f"Gửi mail thất bại: {exc}")

    if export_clicked:
        template = excel_template_path
        if not template.exists():
            st.error(f"Không tìm thấy file mẫu: {template}")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = OUTPUT_DIR / f"form_nhap_lieu_{timestamp}.xlsx"
            try:
                fill_template(template, output, output_values)
                st.success(f"Đã tạo file: {output}")
                st.download_button(
                    "Tải file Excel đã điền",
                    data=output.read_bytes(),
                    file_name=output.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                )
            except Exception as exc:
                st.error(f"Xuất Excel thất bại: {exc}")

    st.subheader("Hồ sơ gần nhất")
    recent = recent_cases(sqlite_db_path, limit=6)
    if recent:
        st.dataframe(display_cases(recent), width="stretch", hide_index=True)
    else:
        st.caption("Chưa có hồ sơ nào trong SQLite.")
