from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.app_config import DATA_DIR, SQLITE_DATABASE, AI_CONFIG_PATH, load_ai_config
from src.backup_service import create_backup
from src.excel_writer import EXCEL_DROPDOWN_LABELS, load_dropdown_options, save_dropdown_options
from src.pdf_exporter import find_soffice_path
from src.template_manager import list_docx_templates, save_template_config


def render_dropdown_option_manager(excel_path: Path) -> None:
    st.subheader("Danh sách chọn trong Form Excel")
    if not excel_path.exists():
        st.error("Không tìm thấy file Excel mẫu để sửa danh sách chọn.")
        return

    try:
        dropdown_options = load_dropdown_options(excel_path)
    except Exception as exc:
        st.error(f"Không đọc được danh sách chọn từ Excel: {exc}")
        return

    field_names = list(EXCEL_DROPDOWN_LABELS.keys())
    selected_field = st.selectbox(
        "Chọn danh sách cần sửa",
        field_names,
        format_func=lambda value: EXCEL_DROPDOWN_LABELS.get(value, value),
        key="dropdown_manager_field",
    )
    current_options = dropdown_options.get(selected_field, [])
    st.caption(f"Đang có {len(current_options)} giá trị trong danh sách `{EXCEL_DROPDOWN_LABELS[selected_field]}`.")

    edited_text = st.text_area(
        "Mỗi dòng là một giá trị",
        value="\n".join(current_options),
        height=260,
        key=f"dropdown_manager_values_{selected_field}",
    )

    action_col1, action_col2 = st.columns([1, 2])
    with action_col1:
        save_clicked = st.button("Lưu danh sách chọn", width="stretch", key="save_dropdown_options")
    with action_col2:
        st.caption("App sẽ xóa dòng trống, bỏ trùng và ghi lại vào vùng danh sách của Excel mẫu.")

    if save_clicked:
        new_options = [line.strip() for line in edited_text.splitlines()]
        try:
            save_dropdown_options(excel_path, selected_field, new_options)
            st.success("Đã cập nhật danh sách chọn trong file Excel mẫu.")
            st.rerun()
        except PermissionError:
            st.error("Không lưu được. Hãy đóng file Excel mẫu nếu đang mở rồi thử lại.")
        except Exception as exc:
            st.error(f"Lưu danh sách chọn thất bại: {exc}")


def render_system_health_check(template_config: dict[str, object]) -> None:
    st.subheader("Kiểm tra sức khỏe hệ thống")
    
    # 1. Database Check
    if SQLITE_DATABASE.exists():
        st.success(f"Cơ sở dữ liệu: OK ({SQLITE_DATABASE.name})")
    else:
        st.error(f"Cơ sở dữ liệu: KHÔNG TÌM THẤY ({SQLITE_DATABASE})")

    # 2. Templates Check
    ind_dir = Path(str(template_config.get("individual_template_dir", "")))
    org_dir = Path(str(template_config.get("organization_template_dir", "")))
    
    for label, directory in [("Mẫu cá nhân", ind_dir), ("Mẫu tổ chức", org_dir)]:
        if directory.exists() and directory.is_dir():
            templates = list_docx_templates(directory)
            if templates:
                st.success(f"{label}: OK ({len(templates)} file .docx)")
            else:
                st.warning(f"{label}: THƯ MỤC TRỐNG ({directory})")
        else:
            st.error(f"{label}: THƯ MỤC KHÔNG TỒN TẠI ({directory})")

    # 3. LibreOffice Check
    soffice = find_soffice_path()
    if soffice:
        st.success(f"Công cụ PDF (LibreOffice): OK")
        st.caption(f"Đường dẫn: `{soffice}`")
    else:
        st.error("Công cụ PDF (LibreOffice): CHƯA CÀI ĐẶT HOẶC KHÔNG TÌM THẤY")
        st.caption("Cần cài đặt LibreOffice để có thể xuất file PDF.")

    # 4. AI Provider Check
    ai_config = load_ai_config(AI_CONFIG_PATH)
    provider = str(ai_config.get("provider", "Gemini"))
    providers_info = ai_config.get("providers", {})
    if isinstance(providers_info, dict):
        p_info = providers_info.get(provider, {})
        if isinstance(p_info, dict) and p_info.get("api_key"):
            st.success(f"AI Provider ({provider}): Cấu hình OK")
        else:
            st.warning(f"AI Provider ({provider}): CHƯA CÓ API KEY")
    
    st.write("---")
    if st.button("Sao lưu dữ liệu ngay", width="stretch"):
        with st.spinner("Đang tạo bản sao lưu..."):
            backup_path = create_backup(DATA_DIR)
            if backup_path:
                st.success(f"Đã tạo bản sao lưu thành công tại: `{backup_path}`")
            else:
                st.error("Không tìm thấy dữ liệu nào để sao lưu.")


def render_data_management() -> None:
    st.subheader("Quản trị dữ liệu")
    from src.data_manager import create_backup, get_backup_bytes, restore_backup, wipe_all_data, list_backups
    
    tab_backup, tab_restore, tab_wipe = st.tabs(["Sao lưu", "Khôi phục", "Xóa trắng"])
    
    with tab_backup:
        st.write("Tạo bản sao lưu toàn bộ cơ sở dữ liệu và cấu hình hệ thống.")
        include_folders = st.checkbox("Bao gồm cả thư mục tài liệu (case_files, uploads)", value=False)
        
        if st.button("Tạo bản sao lưu mới", key="btn_create_backup"):
            with st.spinner("Đang nén dữ liệu..."):
                try:
                    backup_path = create_backup(include_folders=include_folders)
                    backup_bytes = get_backup_bytes(backup_path)
                    filename = Path(backup_path).name
                    
                    st.success(f"Đã tạo bản sao lưu: {filename}")
                    st.download_button(
                        label="📥 Tải bản sao lưu về máy",
                        data=backup_bytes,
                        file_name=filename,
                        mime="application/zip",
                        key="btn_download_backup"
                    )
                except Exception as e:
                    st.error(f"Lỗi khi tạo sao lưu: {e}")
        
        st.write("---")
        st.caption("Các bản sao lưu gần đây trên máy chủ:")
        recent = list_backups()[:5]
        if recent:
            for b in recent:
                st.text(f"📄 {b.name} ({b.stat().st_size // 1024} KB)")
        else:
            st.caption("Chưa có bản sao lưu nào.")

    with tab_restore:
        st.warning("⚠️ **Cảnh báo:** Việc khôi phục sẽ ghi đè toàn bộ dữ liệu hiện tại bằng dữ liệu từ bản sao lưu. Hành động này không thể hoàn tác.")
        uploaded_file = st.file_uploader("Chọn file sao lưu (.zip)", type="zip", key="restore_uploader")
        
        if uploaded_file is not None:
            if st.button("🚀 Tiến hành khôi phục", type="primary", key="btn_execute_restore"):
                with st.spinner("Đang khôi phục dữ liệu..."):
                    try:
                        if restore_backup(uploaded_file):
                            st.success("Khôi phục dữ liệu thành công! Vui lòng tải lại trang.")
                            st.balloons()
                    except Exception as e:
                        st.error(f"Khôi phục thất bại: {e}")

    with tab_wipe:
        st.error("🚨 **KHU VỰC NGUY HIỂM:** Hành động này sẽ xóa sạch toàn bộ hồ sơ và dữ liệu trong hệ thống.")
        st.write("Cấu hình hệ thống (API keys, templates) sẽ được giữ lại, nhưng toàn bộ danh sách hồ sơ và khách hàng sẽ bị xóa.")
        
        confirm_text = st.text_input("Nhập 'XAC NHAN XOA' để tiếp tục:", key="wipe_confirm_text")
        
        if st.button("🔥 XÓA TOÀN BỘ DỮ LIỆU", type="primary", key="btn_wipe_all", disabled=(confirm_text != "XAC NHAN XOA")):
            with st.spinner("Đang xóa dữ liệu..."):
                try:
                    if wipe_all_data(include_logs=True):
                        st.success("Đã xóa toàn bộ dữ liệu thành công.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi xóa dữ liệu: {e}")


def render(
    config_path: Path,
    template_config: dict[str, object],
) -> None:
    tab_config, tab_health, tab_data = st.tabs(["Cấu hình Template", "Sức khỏe hệ thống", "Quản trị dữ liệu"])
    
    with tab_config:
        st.subheader("Cấu hình template")
        with st.form("template_config_form"):
            excel_template_path = st.text_input(
                "File mẫu Excel",
                value=str(template_config["excel_template_path"]),
            )
            individual_template_dir = st.text_input(
                "Thư mục mẫu Word cá nhân",
                value=str(template_config["individual_template_dir"]),
            )
            organization_template_dir = st.text_input(
                "Thư mục mẫu Word tổ chức",
                value=str(template_config["organization_template_dir"]),
            )
            template_editor_name = st.text_input(
                "Tên người chỉnh sửa template",
                value=str(template_config.get("template_editor_name", "")),
            )
            save_clicked = st.form_submit_button("Lưu cấu hình template", type="primary")

        if save_clicked:
            new_config = {
                "excel_template_path": excel_template_path.strip(),
                "individual_template_dir": individual_template_dir.strip(),
                "organization_template_dir": organization_template_dir.strip(),
                "template_editor_name": template_editor_name.strip() or os.getenv("USERNAME", "Unknown"),
                "locked_templates": list(template_config.get("locked_templates", [])),
                "template_labels": dict(template_config.get("template_labels", {})),
            }
            save_template_config(config_path, new_config)
            st.success("Đã lưu cấu hình template.")
            st.rerun()

        excel_path = Path(str(template_config["excel_template_path"]))
        editor_name = str(template_config.get("template_editor_name", os.getenv("USERNAME", "Unknown")))
        st.subheader("Trạng thái đường dẫn")
        st.caption(f"Form Excel: {excel_path}")
        st.caption(f"Người chỉnh sửa hiện tại: {editor_name}")
        if excel_path.exists():
            st.success("Đã tìm thấy file form Excel.")
        else:
            st.error("Không tìm thấy file form Excel theo cấu hình hiện tại.")

        render_dropdown_option_manager(excel_path)
    
    with tab_health:
        render_system_health_check(template_config)
        
    with tab_data:
        render_data_management()
