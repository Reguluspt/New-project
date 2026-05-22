from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.app_config import (
    CASE_FILES_DIR,
    OUTPUT_DIR,
    UNPAID_STATUS,
    reset_entry_workspace,
    selectbox_from_excel,
    sync_form_to_gcn_from_fields,
)
from src.case_files import case_folder, save_original_file
from src.database_store import format_money, parse_money
from src.database_manager import create_outbound_tracking_record, resolve_records_db_path
from src.excel_writer import fill_template
from src.mail_service import send_appraisal_email
from src.models import blank_extraction
from src.sqlite_store import DEFAULT_CASE_STATUS, create_case, display_cases, get_case, recent_cases, update_case
from src.web_automation import missing_web_entry_fields, run_company_web_entry
from views.case_dialogs import open_case_edit_dialog


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


def _entry_has_meaningful_data(values: dict[str, object]) -> bool:
    keys = (
        "contract_number",
        "customer_info",
        "customer_address",
        "asset_description",
        "valuation_purpose",
        "source",
    )
    return any(str(values.get(key) or "").strip() for key in keys)


def _entry_action_payload(sqlite_db_path: Path, output_values: dict[str, object]) -> tuple[dict[str, object], int | None, bool]:
    if _entry_has_meaningful_data(output_values):
        return output_values, None, False
    last_case_id = st.session_state.get("last_saved_case_id")
    if last_case_id:
        saved_case = get_case(sqlite_db_path, int(last_case_id))
        if saved_case:
            return dict(saved_case), int(last_case_id), True
    return output_values, None, False


def _render_missing_web_fields(missing_fields: list[dict[str, str]]) -> None:
    st.error("Hồ sơ còn thiếu thông tin bắt buộc để gửi yêu cầu định giá lên Web.")
    st.dataframe(
        [{"Trường cần bổ sung": item["label"], "Dữ liệu kiểm tra": item["source"]} for item in missing_fields],
        width="stretch",
        hide_index=True,
    )


def render(
    *,
    sqlite_db_path: Path,
    excel_template_path: Path,
    excel_dropdown_options: dict,
) -> None:
    st.subheader("Bước 1 - Kiểm tra và xuất form nhập liệu")
    if st.session_state.get("save_success_message"):
        st.success(st.session_state.pop("save_success_message"))
    extraction = st.session_state.get("extraction") or blank_extraction()

    so_thua = _hidden_gcn_value("so_thua", extraction.so_thua_dat)
    so_to = _hidden_gcn_value("so_to", extraction.so_to_ban_do)
    land_address = _hidden_gcn_value("land_address", extraction.dia_chi_thua_dat)
    owner_name = _hidden_gcn_value("owner_name", extraction.ten_chu_so_huu_cuoi_cung)
    owner_address = _hidden_gcn_value("owner_address", extraction.dia_chi_chu_so_huu_cuoi_cung)
    citizen_id = _hidden_gcn_value("citizen_id", extraction.so_cccd_chu_so_huu_cuoi_cung)

    execution_month = datetime.now().strftime("%m/%Y")
    today_text = datetime.now().strftime("%d/%m/%Y")
    if not str(st.session_state.get("entry_contract_date_ind") or "").strip():
        st.session_state["entry_contract_date_ind"] = today_text
    if not str(st.session_state.get("entry_contract_date_org") or "").strip():
        st.session_state["entry_contract_date_org"] = today_text
    case_status = DEFAULT_CASE_STATUS
    payment_status = UNPAID_STATUS

    # --- Khởi tạo giá trị mặc định cho các trường tổ chức (để output_values luôn có) ---
    tax_code = ""
    representative_name = ""
    representative_position = ""
    handover_contact_name = ""
    handover_contact_position = ""
    handover_contact_phone = ""
    authorization_note = ""

    tab_ca_nhan, tab_to_chuc = st.tabs(["🧑 Khách hàng Cá nhân", "🏢 Khách hàng Tổ chức"])

    with tab_ca_nhan:
        import random
        random_phone = f"09{random.randint(10000000, 99999999)}"
        
        ind_col_top1, ind_col_top2 = st.columns(2)
        with ind_col_top1:
            contract_number_ind = st.text_input("Số hợp đồng", key="entry_contract_number_ind")
        with ind_col_top2:
            contract_date_ind = st.text_input("Ngày hợp đồng", key="entry_contract_date_ind", placeholder="VD: 06/10/2025")
        customer_info_ind = st.text_input("Tên khách hàng", key="entry_customer_info_ind")
        ind_col1, ind_col2, ind_col3 = st.columns(3)
        with ind_col1:
            customer_address_ind = st.text_input("Địa chỉ khách hàng", key="entry_customer_address_ind")
        with ind_col2:
            customer_citizen_id_ind = st.text_input("Số CCCD/CMND", key="entry_citizen_id_ind")
        with ind_col3:
            customer_phone_ind = st.text_input("Số điện thoại", value=random_phone, key="entry_phone_ind")

    def _on_org_select():
        selected = st.session_state.get("entry_org_searchbox")
        if selected and selected != "-- Chọn từ danh bạ hoặc nhập mới --":
            from src.sqlite_store import get_all_organizations
            orgs = get_all_organizations(sqlite_db_path)
            auto_org = next((o for o in orgs if f"{o['name']} ({o.get('tax_code', '')})" == selected), None)
            if auto_org:
                st.session_state.entry_customer_info_org = auto_org.get("name", "")
                st.session_state.entry_customer_address_org = auto_org.get("address", "")
                st.session_state.entry_tax_code = auto_org.get("tax_code", "")
                st.session_state.entry_representative_name = auto_org.get("representative", "")
                st.session_state.entry_representative_position = auto_org.get("position", "")

    with tab_to_chuc:
        org_col_top1, org_col_top2 = st.columns(2)
        with org_col_top1:
            contract_number_org = st.text_input("Số hợp đồng", key="entry_contract_number_org")
        with org_col_top2:
            contract_date_org = st.text_input("Ngày hợp đồng", key="entry_contract_date_org", placeholder="VD: 06/10/2025")
        
        from src.sqlite_store import get_all_organizations
        orgs = get_all_organizations(sqlite_db_path)
        org_options = ["-- Chọn từ danh bạ hoặc nhập mới --"] + [f"{o['name']} ({o.get('tax_code', '')})" for o in orgs]
        st.selectbox("Tìm kiếm từ danh bạ (Mã số thuế / Tên)", org_options, key="entry_org_searchbox", on_change=_on_org_select)
        
        customer_info_org = st.text_input("Tên công ty / tổ chức", key="entry_customer_info_org")
        customer_address_org = st.text_input("Địa chỉ công ty", key="entry_customer_address_org")
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

    # --- Xác định loại khách hàng và gộp thông tin ---
    if customer_info_org:
        customer_type = "organization"
        customer_info = customer_info_org
        customer_address = customer_address_org
        customer_phone = ""
        customer_citizen_id = ""
        contract_number = contract_number_org
        contract_date = contract_date_org
    else:
        customer_type = "individual"
        customer_info = customer_info_ind
        customer_address = customer_address_ind
        customer_phone = customer_phone_ind
        customer_citizen_id = customer_citizen_id_ind
        contract_number = contract_number_ind
        contract_date = contract_date_ind

    # --- Thông tin Nghiệp vụ ---
    st.subheader("Thông tin Nghiệp vụ")
    asset_description = st.text_area("Tài sản thẩm định giá", height=88, key="entry_asset_description")
    asset_type = selectbox_from_excel("Loại tài sản", "asset_type", excel_dropdown_options, "entry_asset_type")
    preliminary_status = selectbox_from_excel("Sơ bộ", "preliminary_status", excel_dropdown_options, "entry_preliminary_status")
    valuation_purpose = selectbox_from_excel("Mục đích thẩm định", "valuation_purpose", excel_dropdown_options, "entry_valuation_purpose")
    source = selectbox_from_excel("Nguồn/đối tác", "source", excel_dropdown_options, "entry_source")
    valuation_fee_number = st.text_input("Phí thẩm định", key="entry_valuation_fee_number", on_change=_format_fee_input)
    advance_payment = st.text_input("Tạm ứng", key="entry_advance_payment")
    valuation_staff = selectbox_from_excel("Chuyên viên nghiệp vụ", "valuation_staff", excel_dropdown_options, "entry_valuation_staff")
    personal_note = st.text_area("Ghi chú cá nhân", height=68, key="entry_personal_note")

    # --- Thông tin Tài sản (GCN) — ẩn trong expander mặc định đóng ---
    with st.expander("📄 Thông tin GCN trích xuất (từ AI)", expanded=False):
        gcn_col1, gcn_col2 = st.columns(2)
        with gcn_col1:
            so_thua = st.text_area("Số thửa đất", value=so_thua, height=68, key="entry_so_thua")
            land_address = st.text_area("Địa chỉ thửa đất", value=land_address, height=68, key="entry_land_address")
            owner_name = st.text_area("Chủ sở hữu cuối cùng", value=owner_name, height=68, key="entry_owner_name")
        with gcn_col2:
            so_to = st.text_area("Số tờ bản đồ", value=so_to, height=68, key="entry_so_to")
            owner_address = st.text_area("Địa chỉ chủ sở hữu", value=owner_address, height=68, key="entry_owner_address")
            citizen_id = st.text_area("CCCD Chủ sở hữu", value=citizen_id, height=68, key="entry_owner_citizen_id")

    output_values = {
        "customer_type": customer_type,
        "case_status": case_status,
        "execution_month": execution_month,
        "payment_status": payment_status,
        "contract_number": contract_number,
        "contract_date": contract_date,
        "asset_type": asset_type,
        "asset_description": asset_description,
        "preliminary_status": preliminary_status,
        "valuation_purpose": valuation_purpose,
        "source": source,
        "customer_info": customer_info,
        "customer_phone": customer_phone,
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

    save_col, export_col, mail_col, web_col = st.columns(4)
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
                saved_original_paths: list[str] = []
                approved_documents = st.session_state.get("entry_approved_documents") or []
                if approved_documents:
                    for document in approved_documents:
                        saved_original = save_original_file(
                            document.get("path"),
                            document.get("original_name") or Path(str(document.get("path") or "")).name,
                            folder,
                        )
                        if saved_original:
                            saved_original_paths.append(str(saved_original))
                else:
                    saved_original = save_original_file(
                        st.session_state.get("uploaded_path"),
                        st.session_state.get("uploaded_original_name", ""),
                        folder,
                    )
                    if saved_original:
                        saved_original_paths.append(str(saved_original))
                update_case(
                    sqlite_db_path,
                    case_id,
                    {
                        **output_values,
                        "case_folder": str(folder),
                        "original_file_path": "\n".join(saved_original_paths),
                    },
                )
                reset_entry_workspace()
                st.session_state["last_saved_case_id"] = case_id
                st.session_state["active_case_id"] = case_id
                st.session_state["save_success_message"] = f"Đã lưu hồ sơ #{case_id} vào SQLite. Các nút gửi mail/Web sẽ ưu tiên dùng hồ sơ vừa lưu nếu form đang trống."
                st.rerun()
            except Exception as exc:
                st.error(f"Lưu SQLite thất bại: {exc}")

    with export_col:
        export_clicked = st.button("Xuất ra Form nhập liệu Excel", type="primary", width="stretch")

    with mail_col:
        mail_clicked = st.button("Gửi mail yêu cầu định giá", width="stretch", icon=":material/mail:")

    with web_col:
        web_clicked = st.button("Gửi yêu cầu lên Web", width="stretch", icon=":material/language:")

    if web_clicked:
        web_payload, saved_case_id, used_saved_case = _entry_action_payload(sqlite_db_path, output_values)
        missing_fields = missing_web_entry_fields(web_payload)
        if missing_fields:
            _render_missing_web_fields(missing_fields)
            if used_saved_case and saved_case_id is not None:
                st.info("Em đã mở popup sửa hồ sơ vừa lưu để anh bổ sung thông tin còn thiếu. Sau khi cập nhật, anh bấm gửi Web lại.")
                open_case_edit_dialog(sqlite_db_path, saved_case_id)
            else:
                st.info("Anh bổ sung các trường còn thiếu ngay trên form nhập hồ sơ rồi bấm gửi Web lại.")
            return
        try:
            with st.spinner("Đang mở trình duyệt để nhập Web..."):
                result = asyncio.run(run_company_web_entry(web_payload, web_url=""))
            st.success(result)
        except Exception as exc:
            st.error(f"Nhập Web thất bại: {exc}")

    if mail_clicked:
        mail_payload, _saved_case_id, used_saved_case = _entry_action_payload(sqlite_db_path, output_values)
        if used_saved_case:
            st.info("Form đang trống nên app dùng hồ sơ vừa lưu để gửi mail, không gửi dữ liệu trắng.")
        try:
            _send_entry_mail(mail_payload)
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
