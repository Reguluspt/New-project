from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.app_config import TEMPLATE_VERSIONS_DIR
from src.template_manager import (
    append_template_history,
    create_template_snapshot,
    get_template_label,
    is_template_locked,
    list_editable_blocks,
    read_template_history,
    save_template_config,
    set_template_label,
    set_template_lock,
    update_template_blocks,
    validate_template_placeholders,
)
from views.template_history import render_template_history


def render_template_editor(
    path: Path,
    customer_type: str,
    *,
    config_path: Path,
    template_config: dict[str, object],
    history_path: Path,
    editor_name: str,
) -> None:
    validation = validate_template_placeholders(path, customer_type)
    placeholders = validation["present"]
    editable_blocks = list_editable_blocks(path, placeholders_only=True)
    locked = is_template_locked(path, list(template_config.get("locked_templates", [])))
    label = get_template_label(path, dict(template_config.get("template_labels", {})))
    history_rows = read_template_history(history_path, template_path=path, limit=10)

    with st.expander(path.name):
        st.caption(str(path))
        st.caption(f"Người đang thao tác: {editor_name}")
        if locked:
            st.warning("Template đang ở chế độ khóa production. Ứng dụng sẽ chặn sửa trực tiếp.")
        else:
            st.info("Template đang mở khóa.")

        selected_label = st.selectbox(
            "Nhãn phiên bản",
            ["production", "draft", "testing"],
            index=["production", "draft", "testing"].index(label if label in {"production", "draft", "testing"} else "draft"),
            key=f"template_label_{customer_type}_{path.name}",
        )
        if st.button(
            "Lưu nhãn phiên bản",
            key=f"save_label_{customer_type}_{path.name}",
            width="stretch",
        ):
            updated_config = dict(template_config)
            updated_config["template_labels"] = set_template_label(
                path,
                dict(template_config.get("template_labels", {})),
                selected_label,
            )
            save_template_config(config_path, updated_config)
            append_template_history(
                history_path,
                template_path=path,
                editor_name=editor_name,
                action="set_template_label",
                details={"label": selected_label},
            )
            st.success("Đã cập nhật nhãn phiên bản.")
            st.rerun()

        lock_col, unlock_col = st.columns(2)
        with lock_col:
            if st.button(
                "Khóa production",
                key=f"lock_{customer_type}_{path.name}",
                width="stretch",
            ):
                updated_config = dict(template_config)
                updated_config["locked_templates"] = set_template_lock(
                    path,
                    list(template_config.get("locked_templates", [])),
                    locked=True,
                )
                save_template_config(config_path, updated_config)
                append_template_history(
                    history_path,
                    template_path=path,
                    editor_name=editor_name,
                    action="lock_template",
                    details={"status": "locked"},
                )
                st.success("Đã khóa template production.")
                st.rerun()
        with unlock_col:
            if st.button(
                "Mở khóa",
                key=f"unlock_{customer_type}_{path.name}",
                width="stretch",
            ):
                updated_config = dict(template_config)
                updated_config["locked_templates"] = set_template_lock(
                    path,
                    list(template_config.get("locked_templates", [])),
                    locked=False,
                )
                save_template_config(config_path, updated_config)
                append_template_history(
                    history_path,
                    template_path=path,
                    editor_name=editor_name,
                    action="unlock_template",
                    details={"status": "unlocked"},
                )
                st.success("Đã mở khóa template.")
                st.rerun()

        if validation["missing"]:
            st.error(
                "Thiếu placeholder bắt buộc: "
                + ", ".join(f"{{{{{name}}}}}" for name in validation["missing"])
            )
        else:
            st.success("Template hợp lệ.")
        if validation["required"]:
            st.caption("Placeholder bắt buộc:")
            st.code("\n".join(f"{{{{{name}}}}}" for name in validation["required"]))
        if placeholders:
            st.caption("Placeholder đang có trong file:")
            st.code("\n".join(f"{{{{{name}}}}}" for name in placeholders))
        else:
            st.info("Không tìm thấy placeholder trong file này.")

        st.caption("Trình sửa nhanh cho các đoạn có placeholder")
        if not editable_blocks:
            st.info("Không có đoạn nào chứa placeholder để sửa nhanh.")
        else:
            block_options = {
                f"{block['location']} | {block['text'][:90]}": block["block_id"] for block in editable_blocks
            }
            selected_block_label = st.selectbox(
                "Chọn đoạn cần sửa",
                list(block_options.keys()),
                key=f"edit_block_select_{customer_type}_{path.name}",
            )
            selected_block_id = block_options[selected_block_label]
            selected_block = next(block for block in editable_blocks if block["block_id"] == selected_block_id)
            if selected_block["placeholders"]:
                st.caption(
                    "Placeholder trong đoạn này: "
                    + ", ".join(f"{{{{{name}}}}}" for name in selected_block["placeholders"])
                )
            edited_text = st.text_area(
                "Nội dung đoạn",
                value=selected_block["text"],
                height=180,
                key=f"edit_block_text_{customer_type}_{path.name}_{selected_block_id}",
                disabled=locked,
            )
            if st.button(
                "Lưu đoạn đang sửa",
                key=f"save_block_{customer_type}_{path.name}_{selected_block_id}",
                disabled=locked,
            ):
                backup_path = create_template_snapshot(path, TEMPLATE_VERSIONS_DIR, reason="before_edit")
                changes = update_template_blocks(path, {selected_block_id: edited_text})
                if changes:
                    for change in changes:
                        append_template_history(
                            history_path,
                            template_path=path,
                            editor_name=editor_name,
                            action="edit_block",
                            details={**change, "backup_path": str(backup_path)},
                        )
                    st.success("Đã cập nhật template.")
                    st.rerun()
                else:
                    st.info("Không có thay đổi nào để lưu.")

        st.caption("Lịch sử chỉnh sửa gần nhất")
        render_template_history(
            history_rows,
            f"history_{customer_type}_{path.name}",
            template_path=path,
            history_path=history_path,
            versions_dir=TEMPLATE_VERSIONS_DIR,
            editor_name=editor_name,
            locked=locked,
        )
