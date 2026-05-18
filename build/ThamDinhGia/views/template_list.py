from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.template_manager import get_template_label, is_template_locked, list_docx_templates, validate_template_placeholders
from views.template_editor import render_template_editor


def render_template_group(
    title: str,
    directory: Path,
    customer_type: str,
    *,
    config_path: Path,
    template_config: dict[str, object],
    history_path: Path,
    editor_name: str,
) -> None:
    st.markdown(f"**{title}**")
    st.caption(str(directory))

    if not directory.exists():
        st.warning("Thư mục template chưa tồn tại.")
        return
    if not directory.is_dir():
        st.error("Đường dẫn đã cấu hình không phải thư mục.")
        return

    template_files = list_docx_templates(directory)
    if not template_files:
        st.info("Không tìm thấy file .docx nào trong thư mục này.")
        return

    summary_rows = []
    for path in template_files:
        validation = validate_template_placeholders(path, customer_type)
        placeholders = validation["present"]
        missing = validation["missing"]
        locked = is_template_locked(path, list(template_config.get("locked_templates", [])))
        label = get_template_label(path, dict(template_config.get("template_labels", {})))
        summary_rows.append(
            {
                "Tệp": path.name,
                "Nhãn": label,
                "Production": "Khóa" if locked else "Mở",
                "Số placeholder": len(placeholders),
                "Bắt buộc": len(validation["required"]),
                "Trạng thái": "OK" if not missing else f"Thiếu {len(missing)} placeholder",
                "Placeholder": ", ".join(f"{{{{{name}}}}}" for name in placeholders),
            }
        )

    st.dataframe(summary_rows, width="stretch", hide_index=True)

    for path in template_files:
        render_template_editor(
            path,
            customer_type,
            config_path=config_path,
            template_config=template_config,
            history_path=history_path,
            editor_name=editor_name,
        )
