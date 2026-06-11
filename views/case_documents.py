from __future__ import annotations

import os
import asyncio
from pathlib import Path

import streamlit as st

from src.app_config import CASE_FILES_DIR, CASE_OUTPUT_CONFIG_PATH
from src.case_exports import (
    approve_case_documents_pdf,
    collect_template_errors,
    compare_case_documents,
    document_action_error,
    export_case_documents,
    package_case_documents,
    preview_case_documents,
    render_document_comparisons,
    render_document_previews,
)
from src.case_files import case_folder, save_original_file
from src.case_output_preferences import load_case_output_dir, save_case_output_dir
from src.database_manager import (
    add_delivery_contact,
    create_outbound_tracking_record,
    ensure_tracking_record_schema,
    get_all_delivery_contacts,
    resolve_records_db_path,
)
from src.mail_service import send_appraisal_email
from src.professional_forwarding import DEFAULT_PROFESSIONAL_RECIPIENT, PROFESSIONAL_RECIPIENT_OPTIONS
from src.pdf_exporter import find_soffice_path
from src.sqlite_store import find_organization_by_query, update_case
from src.web_automation import missing_web_entry_fields, run_company_web_entry
from views.case_dialogs import open_case_edit_dialog


def _ensure_output_dir_state() -> Path:
    if "case_output_dir_value" not in st.session_state:
        st.session_state["case_output_dir_value"] = str(
            load_case_output_dir(CASE_OUTPUT_CONFIG_PATH, default_dir=CASE_FILES_DIR)
        )
    if "case_output_dir_input" not in st.session_state:
        st.session_state["case_output_dir_input"] = st.session_state["case_output_dir_value"]
    return Path(str(st.session_state["case_output_dir_input"]).strip() or str(CASE_FILES_DIR))


def _short_error_message(exc: Exception, *, max_chars: int = 280) -> str:
    message = str(exc).strip()
    first_line = next((line.strip() for line in message.splitlines() if line.strip()), "")
    if not first_line:
        first_line = type(exc).__name__
    if len(first_line) > max_chars:
        return f"{first_line[:max_chars].rstrip()}..."
    return first_line


def _render_web_action_error(exc: Exception) -> None:
    st.error(f"Nhập Web thất bại: {_short_error_message(exc)}")
    detail = str(exc).strip()
    if detail:
        with st.expander("Chi tiết lỗi kỹ thuật", expanded=False):
            st.code(detail, language="text")


def _selected_case_folder(base_dir: Path, *, selected_id: int, case: dict[str, object]) -> Path:
    return case_folder(
        base_dir,
        case_id=selected_id,
        contract_number=str(case.get("contract_number") or ""),
        customer_name=str(case.get("customer_info") or ""),
    )


def _save_output_dir_and_case_folder(
    *,
    db_path: Path | None,
    selected_id: int,
    base_dir: str | Path,
    selected_folder: Path,
    export_case: dict[str, object] | None = None,
) -> Path:
    saved_base_dir = save_case_output_dir(CASE_OUTPUT_CONFIG_PATH, base_dir)
    selected_folder.mkdir(parents=True, exist_ok=True)
    case_updates = {"case_folder": str(selected_folder)}
    if export_case:
        original_value = str(export_case.get("original_file_path") or "").strip()
        original_path = Path(original_value) if original_value else None
        if original_path and original_path.is_file():
            try:
                already_inside_folder = original_path.resolve().is_relative_to(selected_folder.resolve())
            except OSError:
                already_inside_folder = False
            if not already_inside_folder:
                saved_original = save_original_file(original_path, original_path.name, selected_folder)
                if saved_original:
                    export_case["original_file_path"] = str(saved_original)
                    case_updates["original_file_path"] = str(saved_original)
    if db_path is not None:
        update_case(db_path, selected_id, case_updates)
    return saved_base_dir


def _open_folder(path: str | Path) -> None:
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "startfile"):
        try:
            os.startfile(str(folder))
        except Exception:
            pass
    else:
        import subprocess
        import sys
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=True)
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", str(folder)], check=True)
        except Exception:
            pass


def _render_missing_web_fields(missing_fields: list[dict[str, str]]) -> None:
    st.error("Hồ sơ còn thiếu thông tin bắt buộc để gửi yêu cầu định giá lên Web.")
    st.dataframe(
        [{"Trường cần bổ sung": item["label"], "Dữ liệu kiểm tra": item["source"]} for item in missing_fields],
        width="stretch",
        hide_index=True,
    )


def _ensure_web_ready_or_open_edit(
    *,
    export_case: dict[str, object],
    db_path: Path | None,
    selected_id: int,
) -> bool:
    missing_fields = missing_web_entry_fields(export_case)
    if not missing_fields:
        return True
    _render_missing_web_fields(missing_fields)
    if db_path is not None:
        st.info("Em đã mở popup sửa hồ sơ để anh bổ sung các trường còn thiếu. Sau khi cập nhật, anh bấm gửi Web lại.")
        open_case_edit_dialog(db_path, selected_id)
    return False


def _case_for_export(case: dict[str, object] | None, selected_folder: Path) -> dict[str, object] | None:
    if not case:
        return None
    working_case = dict(case)
    working_case["case_folder"] = str(selected_folder)
    return working_case


async def _tracked_case_mail_payload(case: dict[str, object]) -> dict[str, object]:
    records_db_path = Path(resolve_records_db_path())
    record_id = await create_outbound_tracking_record(records_db_path, case, file_path="desktop_case")
    payload = dict(case)
    payload.pop("id", None)
    payload["record_id"] = record_id
    payload["records_db_path"] = str(records_db_path)
    return payload


async def _do_send_case_mail(case: dict[str, object]) -> MailSendResult:
    mail_payload = await _tracked_case_mail_payload(case)
    return await send_appraisal_email(mail_payload)


def _send_case_mail(case: dict[str, object]) -> None:
    result = asyncio.run(_do_send_case_mail(case))
    st.success(f"Đã gửi mail yêu cầu định giá tới {result.to_email}.")
    if result.cc_emails:
        st.caption(f"CC: {', '.join(result.cc_emails)}")


def _professional_forward_options(key_prefix: str) -> dict[str, str]:
    enabled = st.checkbox(
        "Chuyển tiếp cho Nghiệp vụ khi Hành chính trả lời",
        value=True,
        key=f"{key_prefix}_professional_forward_enabled",
    )
    recipient = st.selectbox(
        "Người nhận Nghiệp vụ",
        [DEFAULT_PROFESSIONAL_RECIPIENT, PROFESSIONAL_RECIPIENT_OPTIONS["anhvu"]],
        index=0,
        disabled=not enabled,
        key=f"{key_prefix}_professional_recipient_email",
    )
    return {
        "professional_forward_enabled": "1" if enabled else "0",
        "professional_recipient_email": recipient if enabled else "",
    }


def _render_output_dir_controls(
    *,
    db_path: Path | None,
    selected_id: int,
    refreshed_case: dict[str, object] | None,
) -> tuple[Path, Path, dict[str, object] | None]:
    output_base_dir = _ensure_output_dir_state()
    selected_folder = _selected_case_folder(output_base_dir, selected_id=selected_id, case=refreshed_case or {})

    path_col, save_col, open_col = st.columns([5, 1, 1])
    with path_col:
        st.text_input(
            "Thư mục lưu bộ hồ sơ",
            key="case_output_dir_input",
            help="Nhập hoặc dán đường dẫn thư mục gốc. Mỗi hồ sơ sẽ được lưu trong một thư mục con theo mã hồ sơ.",
        )
    output_base_dir = Path(str(st.session_state.get("case_output_dir_input") or CASE_FILES_DIR).strip())
    selected_folder = _selected_case_folder(output_base_dir, selected_id=selected_id, case=refreshed_case or {})

    with save_col:
        st.write("")
        st.write("")
        if st.button("Lưu", width="stretch", key=f"save_case_output_dir_{selected_id}"):
            try:
                saved_base_dir = _save_output_dir_and_case_folder(
                    db_path=db_path,
                    selected_id=selected_id,
                    base_dir=output_base_dir,
                    selected_folder=selected_folder,
                    export_case=_case_for_export(refreshed_case, selected_folder),
                )
                st.session_state["case_output_dir_value"] = str(saved_base_dir)
                st.success("Đã lưu đường dẫn xuất.")
            except Exception as exc:
                st.error(f"Lưu đường dẫn thất bại: {exc}")
    with open_col:
        st.write("")
        st.write("")
        if st.button("Mở", width="stretch", key=f"open_case_output_dir_{selected_id}", help="Mở thư mục xuất hồ sơ"):
            try:
                saved_base_dir = _save_output_dir_and_case_folder(
                    db_path=db_path,
                    selected_id=selected_id,
                    base_dir=output_base_dir,
                    selected_folder=selected_folder,
                    export_case=_case_for_export(refreshed_case, selected_folder),
                )
                st.session_state["case_output_dir_value"] = str(saved_base_dir)
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Mở thư mục xuất thất bại: {exc}")

    st.caption(f"Thư mục hồ sơ sẽ xuất: {selected_folder}")
    return output_base_dir, selected_folder, _case_for_export(refreshed_case, selected_folder)


def _persist_before_action(
    *,
    db_path: Path | None,
    selected_id: int,
    output_base_dir: Path,
    selected_folder: Path,
    export_case: dict[str, object] | None,
) -> bool:
    try:
        saved_base_dir = _save_output_dir_and_case_folder(
            db_path=db_path,
            selected_id=selected_id,
            base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        )
        st.session_state["case_output_dir_value"] = str(saved_base_dir)
        return True
    except Exception as exc:
        st.error(f"Không thể chuẩn bị thư mục xuất: {exc}")
        return False


async def _load_delivery_contacts() -> list[dict[str, object]]:
    records_db_path = Path(resolve_records_db_path())
    await ensure_tracking_record_schema(records_db_path)
    return await get_all_delivery_contacts(records_db_path)


def _manual_delivery_contact_error(
    *,
    short_name: str,
    details: str,
    save_to_contacts: bool,
    contacts: list[dict[str, object]],
) -> str | None:
    if not details.strip():
        return "Vui lòng nhập thông tin người nhận chuyển phát."
    if not save_to_contacts:
        return None
    if not short_name.strip():
        return "Vui lòng nhập tên gợi nhớ để lưu người nhận vào danh bạ."
    normalized_name = short_name.strip().casefold()
    if any(str(contact.get("short_name") or "").strip().casefold() == normalized_name for contact in contacts):
        return "Tên gợi nhớ đã có trong danh bạ. Vui lòng đổi tên hoặc bỏ chọn lưu vào danh bạ."
    return None


def _case_with_organization_contact_address(
    export_case: dict[str, object],
    db_path: Path | None,
) -> dict[str, object]:
    if str(export_case.get("customer_type") or "").strip() != "organization" or db_path is None:
        return export_case

    query = str(export_case.get("tax_code") or export_case.get("customer_info") or "").strip()
    if not query:
        return export_case

    try:
        organizations = find_organization_by_query(db_path, query)
    except Exception:
        return export_case

    if not organizations:
        return export_case

    organization_address = str(organizations[0].get("address") or "").strip()
    if not organization_address:
        return export_case

    enriched_case = dict(export_case)
    enriched_case["customer_address"] = organization_address
    return enriched_case


def _send_phathanh_mail(export_case: dict[str, object], recipient: str, db_path: Path | None = None) -> None:
    from src.email_reply_service import send_phathanh_email_for_case

    with st.spinner("Đang gửi mail phát hành chứng thư..."):
        mail_case = _case_with_organization_contact_address(export_case, db_path)
        to_email = asyncio.run(send_phathanh_email_for_case(mail_case, recipient=recipient))
    st.success(f"Đã gửi mail phát hành chứng thư thành công tới {to_email}.")


def _mark_phathanh_case_completed(db_path: Path | None, selected_id: int) -> bool:
    if db_path is None:
        return False
    update_case(db_path, selected_id, {"case_status": "Hoàn thành", "cancel_reason": ""})
    return True


def _render_phathanh_delivery_form(
    *,
    export_case: dict[str, object],
    selected_id: int,
    output_base_dir: Path,
    selected_folder: Path,
    db_path: Path | None,
    key_prefix: str,
) -> str | None:
    from src.email_reply_service import DEFAULT_PHATHANH_RECIPIENT

    try:
        contacts = asyncio.run(_load_delivery_contacts())
    except Exception as exc:
        st.error(f"Không thể tải danh bạ chuyển phát: {exc}")
        return None

    saved_recipients: list[tuple[str, str]] = [("VP Gia Lai (mặc định)", DEFAULT_PHATHANH_RECIPIENT)]
    saved_recipients.extend(
        (
            f"{str(contact.get('short_name') or '').strip()} (Danh bạ #{contact.get('id')})",
            str(contact.get("full_details") or "").strip(),
        )
        for contact in contacts
        if str(contact.get("full_details") or "").strip()
    )

    st.markdown("**Thông tin chuyển phát**")
    st.caption("Mail phát hành chỉ được gửi sau khi xác nhận người nhận bên dưới.")
    source = st.radio(
        "Nguồn thông tin người nhận",
        ("Chọn từ danh bạ", "Nhập thủ công"),
        horizontal=True,
        key=f"{key_prefix}_source",
    )
    with st.form(f"{key_prefix}_delivery_form"):
        short_name = ""
        save_to_contacts = False
        if source == "Chọn từ danh bạ":
            selected_index = st.selectbox(
                "Người nhận chuyển phát",
                options=range(len(saved_recipients)),
                format_func=lambda index: saved_recipients[index][0],
                key=f"{key_prefix}_selected_recipient",
            )
            recipient_details = saved_recipients[selected_index][1]
            st.text_area(
                "Thông tin chi tiết",
                value=recipient_details,
                height=112,
                disabled=True,
                key=f"{key_prefix}_selected_details_{selected_index}",
            )
        else:
            short_name = st.text_input(
                "Tên gợi nhớ",
                key=f"{key_prefix}_manual_short_name",
                help="Bắt buộc khi chọn lưu người nhận này vào danh bạ.",
            )
            recipient_details = st.text_area(
                "Thông tin người nhận",
                height=112,
                key=f"{key_prefix}_manual_details",
                placeholder="Tên người nhận hoặc đơn vị\nĐịa chỉ: ...\nĐiện thoại: ...",
            )
            save_to_contacts = st.checkbox(
                "Lưu người nhận này vào danh bạ chuyển phát",
                key=f"{key_prefix}_save_manual_recipient",
            )

        send_clicked = st.form_submit_button("Xác nhận gửi mail", type="primary")
        cancel_clicked = st.form_submit_button("Hủy")

    if cancel_clicked:
        return "cancelled"
    if not send_clicked:
        return None

    if source == "Nhập thủ công":
        error = _manual_delivery_contact_error(
            short_name=short_name,
            details=recipient_details,
            save_to_contacts=save_to_contacts,
            contacts=contacts,
        )
        if error:
            st.error(error)
            return None

    if not _persist_before_action(
        db_path=db_path,
        selected_id=selected_id,
        output_base_dir=output_base_dir,
        selected_folder=selected_folder,
        export_case=export_case,
    ):
        return None

    try:
        _send_phathanh_mail(export_case, recipient_details.strip(), db_path=db_path)
    except Exception as exc:
        st.error(f"Gửi mail phát hành thất bại: {exc}")
        return None

    try:
        if _mark_phathanh_case_completed(db_path, selected_id):
            st.info("Đã chuyển trạng thái hồ sơ sang Hoàn thành.")
    except Exception as exc:
        st.warning(f"Mail đã gửi thành công nhưng không thể chuyển trạng thái hồ sơ sang Hoàn thành: {exc}")

    if source == "Nhập thủ công" and save_to_contacts:
        try:
            asyncio.run(
                add_delivery_contact(
                    Path(resolve_records_db_path()),
                    short_name.strip(),
                    recipient_details.strip(),
                )
            )
            st.info("Đã lưu người nhận vào danh bạ chuyển phát.")
        except Exception as exc:
            st.warning(f"Mail đã gửi thành công nhưng không thể lưu người nhận vào danh bạ: {exc}")
    return "sent"


@st.dialog("Chọn thông tin chuyển phát", width="large")
def open_phathanh_delivery_dialog(
    *,
    selected_id: int,
    export_case: dict[str, object],
    output_base_dir: Path,
    selected_folder: Path,
    db_path: Path | None,
) -> None:
    result = _render_phathanh_delivery_form(
        export_case=export_case,
        selected_id=selected_id,
        output_base_dir=output_base_dir,
        selected_folder=selected_folder,
        db_path=db_path,
        key_prefix=f"quick_phathanh_{selected_id}",
    )
    if result == "cancelled":
        st.rerun()


def _render_file_actions(paths: list[Path], selected_folder: Path) -> None:
    if not paths:
        return
    st.write("---")
    
    # Tự động đóng gói ZIP thư mục hồ sơ và chuẩn bị download trực tiếp
    try:
        with st.spinner("Đang tự động đóng gói trọn bộ ZIP..."):
            archive_path = package_case_documents(selected_folder)
        with open(archive_path, "rb") as f:
            zip_bytes = f.read()
        
        st.success("Tự động đóng gói trọn bộ ZIP hoàn tất! 🎉")
        st.download_button(
            label="Tải về trọn bộ file ZIP 📥 (Nhanh nhất)",
            data=zip_bytes,
            file_name=archive_path.name,
            mime="application/zip",
            key=f"download_zip_auto_{selected_folder.name}_{archive_path.stat().st_mtime}",
            width="stretch"
        )
    except Exception as exc:
        st.warning(f"Tự động đóng gói ZIP thất bại: {exc}")
        
    st.write("")
    st.markdown("**Chi tiết từng file đã xuất:**")
    for path in paths:
        col_text, col_dl, col_open = st.columns([3, 1, 1])
        with col_text:
            st.caption(f"{path.name}")
        with col_dl:
            try:
                with open(path, "rb") as f:
                    file_bytes = f.read()
                st.download_button(
                    label="Tải về 📥",
                    data=file_bytes,
                    file_name=path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if path.suffix == ".docx" else "application/pdf",
                    key=f"download_{path.name}_{path.stat().st_mtime}",
                    width="stretch"
                )
            except Exception as exc:
                st.error(f"Lỗi: {exc}")
        with col_open:
            if st.button("Mở file 🖥️", key=f"open_file_{path.name}_{path.stat().st_mtime}", width="stretch"):
                try:
                    if hasattr(os, "startfile"):
                        os.startfile(str(path))
                    else:
                        import subprocess
                        import sys
                        if sys.platform == "darwin":
                            subprocess.run(["open", str(path)], check=True)
                        elif sys.platform.startswith("linux"):
                            subprocess.run(["xdg-open", str(path)], check=True)
                except Exception as exc:
                    st.warning(f"Không thể mở trực tiếp: {exc}")


@st.dialog("Tùy chọn gửi mail cho nghiệp vụ", width="medium")
def open_quick_mail_dialog(
    *,
    selected_id: int,
    export_case: dict[str, object],
    output_base_dir: Path,
    selected_folder: Path,
    db_path: Path | None,
) -> None:
    st.markdown("**Gửi mail yêu cầu định giá**")
    st.caption("Chọn người nhận và nghiệp vụ chuyển tiếp:")
    professional_options = _professional_forward_options(f"quick_action_mail_{selected_id}")
    
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        send_clicked = st.button("Gửi mail 📧", type="primary", width="stretch")
    with col2:
        cancel_clicked = st.button("Hủy ❌", width="stretch")

    if send_clicked:
        if _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                _send_case_mail({**export_case, **professional_options})
            except Exception as exc:
                st.error(f"Gửi mail thất bại: {exc}")
        st.rerun()
    elif cancel_clicked:
        st.rerun()


def handle_quick_action(
    action: dict[str, object],
    *,
    selected_id: int,
    refreshed_case: dict[str, object] | None,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
    db_path: Path | None = None,
) -> None:
    output_base_dir = _ensure_output_dir_state()
    selected_folder = _selected_case_folder(output_base_dir, selected_id=selected_id, case=refreshed_case or {})
    export_case = _case_for_export(refreshed_case, selected_folder)

    if not export_case:
        st.error("Không tìm thấy hồ sơ để thực hiện thao tác.")
        return

    action_type = action.get("type")

    if action_type == "mail":
        open_quick_mail_dialog(
            selected_id=selected_id,
            export_case=export_case,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            db_path=db_path,
        )

    elif action_type == "mail_phathanh":
        open_phathanh_delivery_dialog(
            selected_id=selected_id,
            export_case=export_case,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            db_path=db_path,
        )

    elif action_type == "web":
        if not _ensure_web_ready_or_open_edit(
            export_case=export_case,
            db_path=db_path,
            selected_id=selected_id,
        ):
            return
        if _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                import sys

                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                with st.spinner("Đang mở trình duyệt để nhập Web..."):
                    result = asyncio.run(run_company_web_entry(export_case, web_url=""))
                st.success(result)
            except Exception as exc:
                _render_web_action_error(exc)

    elif action_type == "export":
        customer_type = (refreshed_case.get("customer_type") or "individual") if refreshed_case else "individual"
        templates_dir = individual_templates_dir if customer_type == "individual" else organization_templates_dir
        template_errors = collect_template_errors(templates_dir, customer_type)
        if customer_type == "organization":
            st.session_state["quick_action"] = dict(action)
            organization_contract_payment = st.radio(
                "Mẫu hợp đồng tổ chức cho xuất nhanh Word",
                ("Không tạm ứng", "Có tạm ứng"),
                horizontal=True,
                key=f"quick_organization_contract_payment_{selected_id}",
            )
            if not st.button(
                "Xuất nhanh bộ hồ sơ Word",
                type="primary",
                width="stretch",
                key=f"confirm_quick_export_word_{selected_id}",
            ):
                st.info("Anh chọn mẫu hợp đồng tổ chức rồi bấm Xuất nhanh bộ hồ sơ Word.")
                return
            st.session_state.pop("quick_action", None)
            export_case = dict(export_case)
            export_case["organization_contract_payment_method"] = (
                "advance" if organization_contract_payment == "Có tạm ứng" else "standard"
            )

        error = document_action_error(
            case=export_case,
            expected_customer_type=customer_type,
            actual_customer_type=customer_type,
            template_errors=template_errors,
        )
        if error:
            st.error(error)
            for item in template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                paths = export_case_documents(
                    export_case,
                    customer_type=customer_type,
                    templates_dir=templates_dir,
                    case_files_dir=output_base_dir,
                )
                st.success(f"Đã xuất nhanh bộ hồ sơ {customer_type}.")
                _render_file_actions(paths, selected_folder)
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Xuất hồ sơ thất bại: {exc}")


def render(
    *,
    selected_id: int,
    case: dict[str, object],
    refreshed_case: dict[str, object] | None,
    effective_case_folder: Path | None,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
    db_path: Path | None = None,
) -> None:
    st.subheader("Xuất bộ hồ sơ")
    output_base_dir, selected_folder, export_case = _render_output_dir_controls(
        db_path=db_path,
        selected_id=selected_id,
        refreshed_case=refreshed_case,
    )
    if effective_case_folder and effective_case_folder != selected_folder:
        st.caption(f"Thư mục đang lưu trong hồ sơ trước đó: {effective_case_folder}")
    if case.get("original_file_path"):
        st.caption(f"File GCN gốc: {case.get('original_file_path')}")

    customer_type_value = (refreshed_case.get("customer_type") or "individual") if refreshed_case else "individual"
    individual_template_errors = collect_template_errors(individual_templates_dir, "individual")
    organization_template_errors = collect_template_errors(organization_templates_dir, "organization")
    soffice_path = find_soffice_path()
    st.caption(f"Công cụ PDF: {soffice_path if soffice_path else 'Chưa tìm thấy soffice.exe'}")

    col1, col2 = st.columns(2)
    with col1:
        preview_individual_clicked = st.button("Xem trước bộ cá nhân", width="stretch")
        compare_individual_clicked = st.button("So sánh preview/file Word cá nhân", width="stretch")
        export_individual_clicked = st.button("Xuất HĐ + PYC + BBNT cá nhân", width="stretch")
        approve_individual_pdf_clicked = st.button(
            "Duyệt và xuất PDF cá nhân",
            width="stretch",
        )
    with col2:
        preview_organization_clicked = st.button("Xem trước bộ tổ chức", width="stretch")
        compare_organization_clicked = st.button("So sánh preview/file Word tổ chức", width="stretch")
        export_organization_clicked = st.button("Xuất bộ hồ sơ tổ chức", width="stretch")
        approve_organization_pdf_clicked = st.button(
            "Duyệt và xuất PDF tổ chức",
            width="stretch",
        )
    organization_contract_payment = st.radio(
        "Mẫu hợp đồng tổ chức",
        ("Không tạm ứng", "Có tạm ứng"),
        horizontal=True,
        key=f"organization_contract_payment_{selected_id}",
    )
    if export_case and customer_type_value == "organization":
        export_case = dict(export_case)
        export_case["organization_contract_payment_method"] = (
            "advance" if organization_contract_payment == "Có tạm ứng" else "standard"
        )
    professional_options = _professional_forward_options(f"case_documents_mail_{selected_id}")
    mail_clicked = st.button("Gửi mail yêu cầu định giá", width="stretch", icon=":material/mail:")
    mail_phathanh_clicked = st.button("Gửi mail phát hành chứng thư", width="stretch", icon=":material/forward_to_inbox:")
    web_clicked = st.button("Gửi yêu cầu định giá lên Web", width="stretch", icon=":material/language:")
    package_clicked = st.button("Đóng gói ZIP hồ sơ", width="stretch")

    if mail_clicked:
        if not export_case:
            st.error("Không tìm thấy hồ sơ để gửi mail.")
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                _send_case_mail({**export_case, **professional_options})
            except Exception as exc:
                st.error(f"Gửi mail thất bại: {exc}")

    delivery_form_state_key = f"show_phathanh_delivery_form_{selected_id}"
    if mail_phathanh_clicked:
        if not export_case:
            st.error("Không tìm thấy hồ sơ để phát hành.")
        else:
            st.session_state[delivery_form_state_key] = True

    if st.session_state.get(delivery_form_state_key) and export_case:
        st.divider()
        delivery_form_result = _render_phathanh_delivery_form(
            export_case=export_case,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            db_path=db_path,
            key_prefix=f"case_documents_phathanh_{selected_id}",
        )
        if delivery_form_result in {"cancelled", "sent"}:
            st.session_state[delivery_form_state_key] = False
            if delivery_form_result == "cancelled":
                st.rerun()

    if web_clicked:
        if not export_case:
            st.error("Không tìm thấy hồ sơ để gửi lên Web.")
        elif not _ensure_web_ready_or_open_edit(
            export_case=export_case,
            db_path=db_path,
            selected_id=selected_id,
        ):
            return
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                with st.spinner("Đang mở trình duyệt để nhập Web..."):
                    result = asyncio.run(run_company_web_entry(export_case, web_url=""))
                st.success(result)
            except Exception as exc:
                _render_web_action_error(exc)

    if preview_individual_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                previews = preview_case_documents(
                    export_case,
                    customer_type="individual",
                    templates_dir=individual_templates_dir,
                    case_files_dir=output_base_dir,
                )
                render_document_previews(previews, f"individual_preview_{selected_id}")
            except Exception as exc:
                st.error(f"Xem trước thất bại: {exc}")

    if compare_individual_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                comparisons = compare_case_documents(
                    export_case,
                    customer_type="individual",
                    templates_dir=individual_templates_dir,
                    case_files_dir=output_base_dir,
                )
                render_document_comparisons(comparisons, f"individual_compare_{selected_id}")
            except Exception as exc:
                st.error(f"So sánh thất bại: {exc}")

    if export_individual_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                paths = export_case_documents(
                    export_case,
                    customer_type="individual",
                    templates_dir=individual_templates_dir,
                    case_files_dir=output_base_dir,
                )
                st.success("Đã xuất bộ hồ sơ cá nhân.")
                _render_file_actions(paths, selected_folder)
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Xuất hồ sơ thất bại: {exc}")

    if approve_individual_pdf_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
            require_pdf=True,
            soffice_path=soffice_path,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                word_paths, pdf_paths = approve_case_documents_pdf(
                    export_case,
                    customer_type="individual",
                    templates_dir=individual_templates_dir,
                    soffice_path=soffice_path,
                    case_files_dir=output_base_dir,
                )
                st.success("Đã duyệt bộ cá nhân và xuất PDF.")
                _render_file_actions(word_paths + pdf_paths, selected_folder)
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Duyệt và xuất PDF thất bại: {exc}")

    if preview_organization_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                previews = preview_case_documents(
                    export_case,
                    customer_type="organization",
                    templates_dir=organization_templates_dir,
                    case_files_dir=output_base_dir,
                )
                render_document_previews(previews, f"organization_preview_{selected_id}")
            except Exception as exc:
                st.error(f"Xem trước thất bại: {exc}")

    if compare_organization_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                comparisons = compare_case_documents(
                    export_case,
                    customer_type="organization",
                    templates_dir=organization_templates_dir,
                    case_files_dir=output_base_dir,
                )
                render_document_comparisons(comparisons, f"organization_compare_{selected_id}")
            except Exception as exc:
                st.error(f"So sánh thất bại: {exc}")

    if export_organization_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                paths = export_case_documents(
                    export_case,
                    customer_type="organization",
                    templates_dir=organization_templates_dir,
                    case_files_dir=output_base_dir,
                )
                st.success("Đã xuất bộ hồ sơ tổ chức.")
                _render_file_actions(paths, selected_folder)
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Xuất hồ sơ tổ chức thất bại: {exc}")

    if approve_organization_pdf_clicked:
        error = document_action_error(
            case=export_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
            require_pdf=True,
            soffice_path=soffice_path,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                word_paths, pdf_paths = approve_case_documents_pdf(
                    export_case,
                    customer_type="organization",
                    templates_dir=organization_templates_dir,
                    soffice_path=soffice_path,
                    case_files_dir=output_base_dir,
                )
                st.success("Đã duyệt bộ tổ chức và xuất PDF.")
                _render_file_actions(word_paths + pdf_paths, selected_folder)
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Duyệt và xuất PDF thất bại: {exc}")

    if package_clicked:
        if not export_case:
            st.error("Không tìm thấy hồ sơ để đóng gói.")
        elif _persist_before_action(
            db_path=db_path,
            selected_id=selected_id,
            output_base_dir=output_base_dir,
            selected_folder=selected_folder,
            export_case=export_case,
        ):
            try:
                with st.spinner("Đang đóng gói ZIP hồ sơ..."):
                    archive_path = package_case_documents(selected_folder)
                st.success("Đã tạo gói ZIP hồ sơ thành công! 🎉")
                st.caption(f"Đường dẫn lưu trên VPS: {archive_path}")
                
                # Đọc dữ liệu file zip để phục vụ download trực tiếp
                with open(archive_path, "rb") as f:
                    zip_bytes = f.read()
                
                st.download_button(
                    label="Tải về file ZIP ngay 📥",
                    data=zip_bytes,
                    file_name=archive_path.name,
                    mime="application/zip",
                    key=f"download_zip_{selected_id}_{archive_path.stat().st_mtime}",
                    width="stretch"
                )
                _open_folder(selected_folder)
            except Exception as exc:
                st.error(f"Đóng gói ZIP thất bại: {exc}")
