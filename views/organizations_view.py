from __future__ import annotations

import pandas as pd
import streamlit as st

from src.sqlite_store import add_organization, delete_organization, get_all_organizations, update_organization


def _render_org_styles() -> None:
    st.markdown(
        """
        <style>
            .org-page-title {
                margin: 0;
                color: var(--app-text);
                font-size: 30px;
                line-height: 36px;
                font-weight: 750;
            }
            .org-caption {
                margin: 4px 0 14px;
                color: var(--app-muted);
                font-size: 13px;
                line-height: 1.45;
            }
            .org-kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
                margin: 10px 0 14px;
            }
            .org-kpi {
                min-height: 82px;
                padding: 14px 16px;
                border: 1px solid var(--app-outline);
                border-radius: 12px;
                background: #fff;
            }
            .org-kpi.primary {
                color: #fff;
                background: var(--app-primary);
                border-color: var(--app-primary);
                box-shadow: 0 8px 18px rgba(15,108,189,.18);
            }
            .org-kpi label {
                display: block;
                color: var(--app-muted);
                font-size: 12px;
                font-weight: 760;
                text-transform: uppercase;
                letter-spacing: .04em;
            }
            .org-kpi.primary label { color: rgba(255,255,255,.78); }
            .org-kpi b {
                display: block;
                margin-top: 8px;
                font-size: 27px;
                line-height: 1;
            }
            .org-panel-title {
                margin: 0 0 2px;
                font-size: 18px;
                line-height: 24px;
                font-weight: 750;
            }
            .org-panel-sub {
                color: var(--app-muted);
                font-size: 12px;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(orgs: list[dict[str, object]]) -> None:
    total = len(orgs)
    with_tax = sum(1 for org in orgs if str(org.get("tax_code") or "").strip())
    with_rep = sum(1 for org in orgs if str(org.get("representative") or "").strip())
    pending_ai = len(st.session_state.get("org_extraction_results", []) or [])
    st.markdown(
        f"""
        <div class="org-kpi-grid">
            <div class="org-kpi primary"><label>Tổng tổ chức</label><b>{total}</b></div>
            <div class="org-kpi"><label>Đã có MST</label><b>{with_tax}</b></div>
            <div class="org-kpi"><label>Có đại diện</label><b>{with_rep}</b></div>
            <div class="org-kpi"><label>Kết quả AI chờ duyệt</label><b>{pending_ai}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _display_organizations(orgs: list[dict[str, object]]) -> None:
    st.markdown('<div class="org-panel-title">Danh sách tổ chức</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="org-panel-sub">Dữ liệu dùng để tự động điền thông tin khách hàng tổ chức khi nhập hồ sơ.</div>',
        unsafe_allow_html=True,
    )
    if not orgs:
        st.info("Chưa có dữ liệu danh bạ tổ chức.")
        return

    display_df = pd.DataFrame(orgs)[
        ["id", "tax_code", "name", "abbreviation", "address", "representative", "position"]
    ].copy()
    display_df.columns = [
        "ID",
        "Mã số thuế",
        "Tên công ty",
        "Tên viết tắt",
        "Địa chỉ",
        "Người đại diện",
        "Chức vụ",
    ]
    st.dataframe(display_df, width="stretch", hide_index=True, height=430)


def _org_options(orgs: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {f"{org.get('name') or 'Chưa có tên'} ({org.get('tax_code') or 'chưa có MST'})": org for org in orgs}


def _render_editor(sqlite_db_path: str, orgs: list[dict[str, object]]) -> None:
    st.markdown('<div class="org-panel-title">Thêm / cập nhật tổ chức</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="org-panel-sub">Giữ form ở panel riêng để không làm rối bảng danh sách.</div>',
        unsafe_allow_html=True,
    )

    mode = st.segmented_control(
        "Chế độ",
        ["Thêm mới", "Cập nhật", "Xóa"],
        default="Thêm mới",
        key="org_editor_mode",
        label_visibility="collapsed",
    )

    selected_org: dict[str, object] | None = None
    if mode in {"Cập nhật", "Xóa"}:
        options = _org_options(orgs)
        if not options:
            st.warning("Chưa có tổ chức nào để thao tác.")
            return
        selected_key = st.selectbox("Chọn tổ chức", list(options.keys()), key="org_selected_key")
        selected_org = options[selected_key]

    if mode == "Xóa":
        assert selected_org is not None
        st.warning(f"Xóa tổ chức: {selected_org.get('name') or 'Chưa có tên'}?")
        if st.button("Xóa tổ chức", type="primary", width="stretch", icon=":material/delete:"):
            delete_organization(sqlite_db_path, int(selected_org["id"]))
            st.success("Đã xóa tổ chức.")
            st.rerun()
        return

    defaults = selected_org or {}
    with st.form("organization_editor_form"):
        tax_code = st.text_input("Mã số thuế", value=str(defaults.get("tax_code") or ""))
        name = st.text_input("Tên công ty *", value=str(defaults.get("name") or ""))
        abbreviation = st.text_input("Tên viết tắt", value=str(defaults.get("abbreviation") or ""))
        address = st.text_input("Địa chỉ", value=str(defaults.get("address") or ""))
        representative = st.text_input("Người đại diện", value=str(defaults.get("representative") or ""))
        position = st.text_input("Chức vụ", value=str(defaults.get("position") or ""))
        submitted = st.form_submit_button(
            "Cập nhật" if mode == "Cập nhật" else "Thêm mới",
            type="primary",
            width="stretch",
        )

    if not submitted:
        return

    if not name.strip():
        st.error("Tên công ty là bắt buộc.")
        return

    data = {
        "tax_code": tax_code.strip(),
        "name": name.strip(),
        "abbreviation": abbreviation.strip(),
        "address": address.strip(),
        "representative": representative.strip(),
        "position": position.strip(),
    }
    if mode == "Cập nhật" and selected_org:
        update_organization(sqlite_db_path, int(selected_org["id"]), data)
        st.success(f"Đã cập nhật tổ chức: {name.strip()}")
    else:
        add_organization(sqlite_db_path, data)
        st.success(f"Đã thêm tổ chức: {name.strip()}")
    st.rerun()


def _render_ai_import(sqlite_db_path: str, api_key: str, model: str) -> None:
    with st.expander("Trích xuất tổ chức từ hợp đồng bằng AI", expanded=False):
        st.caption("Tải lên hợp đồng cũ để AI trích xuất thông tin khách hàng tổ chức. Kiểm tra lại trước khi lưu vào danh bạ.")
        uploaded_files = st.file_uploader(
            "Chọn file hợp đồng",
            type=["pdf", "png", "jpg", "jpeg", "docx"],
            accept_multiple_files=True,
            key="org_contract_uploads",
        )
        if uploaded_files and st.button("Trích xuất hàng loạt bằng AI", type="primary"):
            from src.app_config import DATA_DIR
            from src.gemini_extractor import extract_organization_from_contract_with_gemini

            if not api_key:
                st.error("Chưa cấu hình Gemini API Key.")
                return

            upload_dir = DATA_DIR / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            results: list[dict[str, str]] = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for index, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Đang xử lý: {uploaded_file.name} ({index + 1}/{len(uploaded_files)})...")
                file_path = upload_dir / uploaded_file.name
                file_path.write_bytes(uploaded_file.getbuffer())
                try:
                    extraction = extract_organization_from_contract_with_gemini(file_path, api_key=api_key, model=model)
                    results.append(
                        {
                            "tax_code": extraction.tax_code,
                            "name": extraction.name,
                            "abbreviation": "",
                            "address": extraction.address,
                            "representative": extraction.representative,
                            "position": extraction.position,
                        }
                    )
                except Exception as exc:
                    st.error(f"Lỗi trích xuất file {uploaded_file.name}: {exc}")
                progress_bar.progress((index + 1) / len(uploaded_files))

            status_text.text("Hoàn tất trích xuất.")
            st.session_state["org_extraction_results"] = results

        if "org_extraction_results" not in st.session_state:
            return

        results = st.session_state["org_extraction_results"]
        st.success(f"Trích xuất được {len(results)} tổ chức. Kiểm tra và chỉnh sửa trước khi lưu.")
        edited_df = st.data_editor(pd.DataFrame(results), num_rows="dynamic", width="stretch", key="org_ai_results_editor")
        if st.button("Lưu tất cả vào danh bạ", type="primary", width="stretch"):
            saved_count = 0
            for _, row in edited_df.iterrows():
                name = str(row.get("name", "")).strip()
                if not name:
                    continue
                add_organization(sqlite_db_path, row.to_dict())
                saved_count += 1
            st.success(f"Đã lưu {saved_count} tổ chức vào danh bạ.")
            del st.session_state["org_extraction_results"]
            st.rerun()


def render(sqlite_db_path: str, api_key: str, model: str) -> None:
    _render_org_styles()
    st.markdown('<h1 class="org-page-title">Danh bạ tổ chức</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="org-caption">Quản lý mã số thuế, địa chỉ, người đại diện và chức vụ để tự động điền khi nhập hồ sơ.</div>',
        unsafe_allow_html=True,
    )

    orgs = get_all_organizations(sqlite_db_path)
    _render_kpis(orgs)

    left, right = st.columns([1.8, 1], gap="large")
    with left:
        _display_organizations(orgs)
        _render_ai_import(sqlite_db_path, api_key, model)
    with right:
        _render_editor(sqlite_db_path, orgs)
