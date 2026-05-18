from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.template_manager import append_template_history, create_template_snapshot, restore_template_from_snapshot


def render_template_history(
    history_rows: list[dict[str, object]],
    prefix: str,
    *,
    template_path: Path,
    history_path: Path,
    versions_dir: Path,
    editor_name: str,
    locked: bool,
) -> None:
    if not history_rows:
        st.caption("Chưa có lịch sử chỉnh sửa.")
        return

    for index, item in enumerate(history_rows, start=1):
        details = item.get("details", {})
        title = f"{item.get('timestamp', '')} | {item.get('editor_name', '')} | {item.get('action', '')}"
        with st.expander(title, expanded=index == 1):
            backup_path = str(details.get("backup_path", "")).strip()
            if backup_path:
                st.caption(f"Bản sao lưu: {backup_path}")
            if item.get("action") == "edit_block":
                st.caption(str(details.get("location", "")))
                left, right = st.columns(2)
                with left:
                    st.text_area(
                        "Nội dung cũ",
                        value=str(details.get("old_text", "")),
                        height=140,
                        key=f"{prefix}_old_{index}",
                    )
                with right:
                    st.text_area(
                        "Nội dung mới",
                        value=str(details.get("new_text", "")),
                        height=140,
                        key=f"{prefix}_new_{index}",
                    )
            else:
                st.json(details)

            can_restore = bool(backup_path) and Path(backup_path).exists()
            if can_restore:
                if st.button(
                    "Khôi phục về mốc này",
                    key=f"{prefix}_restore_{index}",
                    disabled=locked,
                    width="stretch",
                ):
                    current_snapshot = create_template_snapshot(template_path, versions_dir, reason="before_restore")
                    restore_template_from_snapshot(template_path, backup_path)
                    append_template_history(
                        history_path,
                        template_path=template_path,
                        editor_name=editor_name,
                        action="restore_template",
                        details={
                            "restored_from": backup_path,
                            "previous_version_backup": str(current_snapshot),
                        },
                    )
                    st.success("Đã khôi phục template từ lịch sử.")
                    st.rerun()
