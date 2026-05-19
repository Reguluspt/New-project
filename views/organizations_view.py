import streamlit as st
import pandas as pd
from src.sqlite_store import get_all_organizations, add_organization, update_organization, delete_organization

def render(sqlite_db_path: str, api_key: str, model: str):
    st.header("🏢 Quản lý Danh bạ Tổ chức")
    st.markdown("Quản lý thông tin khách hàng tổ chức để tự động điền (auto-fill) khi nhập hồ sơ.")

    orgs = get_all_organizations(sqlite_db_path)

    # 1. Hiển thị danh sách và Xóa
    st.subheader("Danh sách Tổ chức")
    if orgs:
        df = pd.DataFrame(orgs)
        # Format df for display
        display_df = df[["id", "tax_code", "name", "abbreviation", "address", "representative", "position"]].copy()
        display_df.columns = ["ID", "Mã số thuế", "Tên Công ty", "Tên viết tắt", "Địa chỉ", "Người đại diện", "Chức vụ"]
        st.dataframe(display_df, width="stretch", hide_index=True)
    else:
        st.info("Chưa có dữ liệu danh bạ tổ chức.")

    # 2. Thêm/Sửa Tổ chức
    st.subheader("Thêm / Cập nhật Tổ chức")
    
    action = st.radio("Thao tác", ["Thêm mới", "Thêm từ Hợp đồng (AI)", "Cập nhật", "Xóa"], horizontal=True)

    if action == "Thêm mới":
        with st.form("add_org_form"):
            tax_code = st.text_input("Mã số thuế")
            name = st.text_input("Tên Công ty *")
            abbreviation = st.text_input("Tên viết tắt")
            address = st.text_input("Địa chỉ")
            representative = st.text_input("Người đại diện")
            position = st.text_input("Chức vụ")
            
            submitted = st.form_submit_button("Thêm mới", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Tên Công ty là bắt buộc.")
                else:
                    data = {
                        "tax_code": tax_code,
                        "name": name,
                        "abbreviation": abbreviation,
                        "address": address,
                        "representative": representative,
                        "position": position
                    }
                    add_organization(sqlite_db_path, data)
                    st.success(f"Đã thêm tổ chức: {name}")
                    st.rerun()

    elif action == "Cập nhật":
        if not orgs:
            st.warning("Không có tổ chức nào để cập nhật.")
        else:
            org_options = {f"{o['name']} ({o.get('tax_code', '')})": o for o in orgs}
            selected_org_key = st.selectbox("Chọn tổ chức để cập nhật", list(org_options.keys()))
            if selected_org_key:
                selected_org = org_options[selected_org_key]
                with st.form("update_org_form"):
                    tax_code = st.text_input("Mã số thuế", value=selected_org.get("tax_code", ""))
                    name = st.text_input("Tên Công ty *", value=selected_org.get("name", ""))
                    abbreviation = st.text_input("Tên viết tắt", value=selected_org.get("abbreviation", ""))
                    address = st.text_input("Địa chỉ", value=selected_org.get("address", ""))
                    representative = st.text_input("Người đại diện", value=selected_org.get("representative", ""))
                    position = st.text_input("Chức vụ", value=selected_org.get("position", ""))
                    
                    submitted = st.form_submit_button("Cập nhật", type="primary")
                    if submitted:
                        if not name.strip():
                            st.error("Tên Công ty là bắt buộc.")
                        else:
                            data = {
                                "tax_code": tax_code,
                                "name": name,
                                "abbreviation": abbreviation,
                                "address": address,
                                "representative": representative,
                                "position": position
                            }
                            update_organization(sqlite_db_path, selected_org["id"], data)
                            st.success(f"Đã cập nhật tổ chức: {name}")
                            st.rerun()

    elif action == "Xóa":
        if not orgs:
            st.warning("Không có tổ chức nào để xóa.")
        else:
            org_options = {f"{o['name']} ({o.get('tax_code', '')})": o for o in orgs}
            selected_org_key = st.selectbox("Chọn tổ chức để xóa", list(org_options.keys()))
            if selected_org_key:
                selected_org = org_options[selected_org_key]
                st.warning(f"Bạn có chắc chắn muốn xóa: {selected_org['name']}?")
                if st.button("Xóa tổ chức", type="primary"):
                    delete_organization(sqlite_db_path, selected_org["id"])
                    st.success("Đã xóa tổ chức.")
                    st.rerun()

    elif action == "Thêm từ Hợp đồng (AI)":
        st.info("Tải lên hàng loạt hợp đồng cũ (PDF/DOCX) để AI tự động trích xuất thông tin khách hàng tổ chức (Bên A/Bên B).")
        uploaded_files = st.file_uploader("Chọn file hợp đồng", type=["pdf", "png", "jpg", "jpeg", "docx"], accept_multiple_files=True)
        if uploaded_files:
            if st.button("Trích xuất hàng loạt bằng AI", type="primary"):
                from src.app_config import DATA_DIR
                from src.gemini_extractor import extract_organization_from_contract_with_gemini
                
                if not api_key:
                    st.error("Chưa cấu hình Gemini API Key.")
                else:
                    upload_dir = DATA_DIR / "uploads"
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    
                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, uploaded_file in enumerate(uploaded_files):
                        status_text.text(f"Đang xử lý: {uploaded_file.name} ({i+1}/{len(uploaded_files)})...")
                        file_path = upload_dir / uploaded_file.name
                        file_path.write_bytes(uploaded_file.getbuffer())
                        
                        try:
                            extraction = extract_organization_from_contract_with_gemini(
                                file_path, api_key=api_key, model=model
                            )
                            results.append({
                                "tax_code": extraction.tax_code,
                                "name": extraction.name,
                                "abbreviation": "",
                                "address": extraction.address,
                                "representative": extraction.representative,
                                "position": extraction.position,
                            })
                        except Exception as e:
                            st.error(f"Lỗi trích xuất file {uploaded_file.name}: {e}")
                            
                        progress_bar.progress((i + 1) / len(uploaded_files))
                        
                    status_text.text("Hoàn tất trích xuất!")
                    st.session_state["org_extraction_results"] = results
        
        if "org_extraction_results" in st.session_state:
            res_list = st.session_state["org_extraction_results"]
            st.success(f"Trích xuất thành công {len(res_list)} tổ chức! Vui lòng kiểm tra bảng bên dưới và chỉnh sửa trực tiếp nếu cần, sau đó bấm Lưu.")
            
            df = pd.DataFrame(res_list)
            edited_df = st.data_editor(df, num_rows="dynamic", width="stretch")
            
            if st.button("Lưu tất cả vào Danh bạ", type="primary"):
                saved_count = 0
                for _, row in edited_df.iterrows():
                    name = str(row.get("name", "")).strip()
                    if name:
                        add_organization(sqlite_db_path, row.to_dict())
                        saved_count += 1
                
                st.success(f"Đã lưu thành công {saved_count} tổ chức vào Danh bạ.")
                del st.session_state["org_extraction_results"]
                st.rerun()
