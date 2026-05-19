
import streamlit as st
import pandas as pd
from src.database_manager import get_all_delivery_contacts, add_delivery_contact, resolve_records_db_path
import aiosqlite
import asyncio

def render(records_db_path):
    st.header("🚚 Danh bạ Chuyển phát")
    st.info("Danh sách người nhận hồ sơ phát hành chứng thư. Bạn có thể chỉnh sửa trực tiếp thông tin tại đây.")

    # Load data
    try:
        # Use a safer way to run async in Streamlit thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        contacts = loop.run_until_complete(get_all_delivery_contacts(records_db_path))
    except Exception as e:
        st.error(f"Lỗi khi tải danh bạ: {e}")
        return
    
    if not contacts:
        st.warning("Chưa có dữ liệu danh bạ chuyển phát.")
        if st.button("Tạo dữ liệu mẫu"):
            loop.run_until_complete(add_delivery_contact(records_db_path, "Mẫu: VP Gia Lai", "VP Gia Lai\n90/60/3 Trường Chinh\n0905226968"))
            st.rerun()
        return

    df = pd.DataFrame(contacts)
    # Rename columns for display
    df_display = df.rename(columns={
        "short_name": "Tên gợi nhớ (Cột trái)",
        "full_details": "Thông tin chi tiết (Cột phải)",
        "id": "ID"
    })

    # Display editor
    edited_df = st.data_editor(
        df_display[["ID", "Tên gợi nhớ (Cột trái)", "Thông tin chi tiết (Cột phải)"]],
        width="stretch",
        num_rows="dynamic",
        key="delivery_contacts_editor",
        disabled=["ID"]
    )

    if st.button("💾 Lưu thay đổi"):
        # Logic to sync back to DB
        loop.run_until_complete(sync_changes(records_db_path, edited_df, df))
        st.success("Đã lưu thay đổi danh bạ thành công!")
        st.rerun()

async def sync_changes(db_path, edited_df, original_df):
    db_path = resolve_records_db_path(db_path)
    from src.email_utils import format_recipient_info
    async with aiosqlite.connect(db_path, timeout=30) as db:
        # Simple sync: Delete all and re-insert for now
        await db.execute("DELETE FROM delivery_contacts")
        for _, row in edited_df.iterrows():
            s_name = str(row["Tên gợi nhớ (Cột trái)"]).strip()
            f_details = format_recipient_info(str(row["Thông tin chi tiết (Cột phải)"]).strip())
            if s_name and f_details:
                await db.execute(
                    "INSERT INTO delivery_contacts (short_name, full_details) VALUES (?, ?)",
                    (s_name, f_details)
                )
        await db.commit()
