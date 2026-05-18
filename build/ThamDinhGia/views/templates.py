from __future__ import annotations

from pathlib import Path

import streamlit as st

from views.template_list import render_template_group


def render(
    config_path: Path,
    template_config: dict[str, object],
    history_path: Path,
) -> None:
    editor_name = str(template_config.get("template_editor_name", "Unknown"))
    st.subheader("Quản lý Templates")
    st.caption(f"Người chỉnh sửa hiện tại: {editor_name}")

    left, right = st.columns(2, gap="large")
    with left:
        render_template_group(
            "Mẫu cá nhân",
            Path(str(template_config["individual_template_dir"])),
            "individual",
            config_path=config_path,
            template_config=template_config,
            history_path=history_path,
            editor_name=editor_name,
        )
    with right:
        render_template_group(
            "Mẫu tổ chức",
            Path(str(template_config["organization_template_dir"])),
            "organization",
            config_path=config_path,
            template_config=template_config,
            history_path=history_path,
            editor_name=editor_name,
        )
