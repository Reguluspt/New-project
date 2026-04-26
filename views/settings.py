from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.excel_writer import EXCEL_DROPDOWN_LABELS, load_dropdown_options, save_dropdown_options
from src.template_manager import save_template_config


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


def render(
    config_path: Path,
    template_config: dict[str, object],
) -> None:
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
