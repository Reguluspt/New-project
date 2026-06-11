from __future__ import annotations

import asyncio

import aiosqlite
import pandas as pd
import streamlit as st

from src.database_manager import add_delivery_contact, get_all_delivery_contacts, resolve_records_db_path


def _event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _render_delivery_styles() -> None:
    st.markdown(
        """
        <style>
            .delivery-page-title {
                margin: 0;
                color: var(--app-text);
                font-size: 30px;
                line-height: 36px;
                font-weight: 750;
            }
            .delivery-caption {
                margin: 4px 0 14px;
                color: var(--app-muted);
                font-size: 13px;
                line-height: 1.45;
            }
            .delivery-kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
                margin: 10px 0 14px;
            }
            .delivery-kpi {
                min-height: 82px;
                padding: 14px 16px;
                border: 1px solid var(--app-outline);
                border-radius: 12px;
                background: #fff;
            }
            .delivery-kpi.primary {
                color: #fff;
                background: var(--app-primary);
                border-color: var(--app-primary);
                box-shadow: 0 8px 18px rgba(15,108,189,.18);
            }
            .delivery-kpi label {
                display: block;
                color: var(--app-muted);
                font-size: 12px;
                font-weight: 760;
                text-transform: uppercase;
                letter-spacing: .04em;
            }
            .delivery-kpi.primary label { color: rgba(255,255,255,.78); }
            .delivery-kpi b {
                display: block;
                margin-top: 8px;
                font-size: 27px;
                line-height: 1;
            }
            .delivery-panel-title {
                margin: 0 0 2px;
                font-size: 18px;
                line-height: 24px;
                font-weight: 750;
            }
            .delivery-panel-sub {
                color: var(--app-muted);
                font-size: 12px;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(contacts: list[dict[str, object]]) -> None:
    total = len(contacts)
    complete = sum(
        1
        for contact in contacts
        if str(contact.get("short_name") or "").strip() and len(str(contact.get("full_details") or "").splitlines()) >= 2
    )
    needs_review = max(total - complete, 0)
    draft_rows = 1 if st.session_state.get("delivery_show_create_form") else 0
    st.markdown(
        f"""
        <div class="delivery-kpi-grid">
            <div class="delivery-kpi primary"><label>Tổng liên hệ</label><b>{total}</b></div>
            <div class="delivery-kpi"><label>Liên hệ đầy đủ</label><b>{complete}</b></div>
            <div class="delivery-kpi"><label>Cần bổ sung</label><b>{needs_review}</b></div>
            <div class="delivery-kpi"><label>Bản nháp mới</label><b>{draft_rows}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _contact_display_df(contacts: list[dict[str, object]]) -> pd.DataFrame:
    df = pd.DataFrame(contacts)
    if df.empty:
        return pd.DataFrame(columns=["ID", "Tên gợi nhớ", "Thông tin chi tiết"])
    return df.rename(
        columns={
            "id": "ID",
            "short_name": "Tên gợi nhớ",
            "full_details": "Thông tin chi tiết",
        }
    )[["ID", "Tên gợi nhớ", "Thông tin chi tiết"]]


def render(records_db_path) -> None:
    _render_delivery_styles()
    st.markdown('<h1 class="delivery-page-title">Danh bạ chuyển phát</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="delivery-caption">Quản lý người nhận hồ sơ phát hành chứng thư, địa chỉ, điện thoại và nội dung dùng khi gửi mail.</div>',
        unsafe_allow_html=True,
    )

    loop = _event_loop()
    try:
        contacts = loop.run_until_complete(get_all_delivery_contacts(records_db_path))
    except Exception as exc:
        st.error(f"Lỗi khi tải danh bạ: {exc}")
        return

    _render_kpis(contacts)

    if not contacts:
        st.warning("Chưa có dữ liệu danh bạ chuyển phát.")
        if st.button("Tạo dữ liệu mẫu", type="primary"):
            loop.run_until_complete(
                add_delivery_contact(
                    records_db_path,
                    "Mẫu: VP Gia Lai",
                    "VP Gia Lai\n90/60/3 Trường Chinh\n0905226968",
                )
            )
            st.rerun()
        return

    left, right = st.columns([1.8, 1], gap="large")
    with left:
        head_col, action_col = st.columns([1, 0.32], vertical_alignment="center")
        with head_col:
            st.markdown('<div class="delivery-panel-title">Danh sách người nhận</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="delivery-panel-sub">Có thể sửa trực tiếp trong bảng rồi bấm lưu thay đổi.</div>',
                unsafe_allow_html=True,
            )
        with action_col:
            if st.button("Tạo danh bạ mới", type="primary", width="stretch", icon=":material/add:"):
                st.session_state["delivery_show_create_form"] = True

        display_df = _contact_display_df(contacts)
        edited_df = st.data_editor(
            display_df,
            width="stretch",
            height=500,
            num_rows="dynamic",
            key="delivery_contacts_editor",
            disabled=["ID"],
        )
        if st.button("Lưu thay đổi", type="primary", width="stretch", icon=":material/save:"):
            loop.run_until_complete(sync_changes(records_db_path, edited_df))
            st.success("Đã lưu thay đổi danh bạ chuyển phát.")
            st.rerun()

    with right:
        st.markdown('<div class="delivery-panel-title">Tạo danh bạ mới</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="delivery-panel-sub">Nhập nhanh liên hệ mới, sau khi tạo sẽ xuất hiện trong bảng bên trái.</div>',
            unsafe_allow_html=True,
        )
        with st.form("delivery_create_form"):
            short_name = st.text_input("Tên gợi nhớ", placeholder="Ví dụ: VP Gia Lai")
            recipient = st.text_input("Đơn vị / người nhận", placeholder="Ví dụ: VP Gia Lai")
            address = st.text_area("Địa chỉ", height=84, placeholder="90/60/3 Trường Chinh, Pleiku")
            phone = st.text_input("Điện thoại", placeholder="0905226968")
            note = st.text_area("Ghi chú / dòng bổ sung", height=84)
            submitted = st.form_submit_button("Tạo mới", type="primary", width="stretch")

        if submitted:
            details = "\n".join(part.strip() for part in [recipient, address, phone, note] if part and part.strip())
            if not short_name.strip() or not details.strip():
                st.error("Cần nhập tên gợi nhớ và ít nhất một dòng thông tin chi tiết.")
            else:
                loop.run_until_complete(add_delivery_contact(records_db_path, short_name.strip(), details))
                st.success("Đã tạo danh bạ mới.")
                st.session_state["delivery_show_create_form"] = False
                st.rerun()


async def sync_changes(db_path, edited_df: pd.DataFrame) -> None:
    db_path = resolve_records_db_path(db_path)
    from src.email_utils import format_recipient_info

    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("DELETE FROM delivery_contacts")
        for _, row in edited_df.iterrows():
            short_name = str(row.get("Tên gợi nhớ") or "").strip()
            full_details = format_recipient_info(str(row.get("Thông tin chi tiết") or "").strip())
            if short_name and full_details:
                await db.execute(
                    "INSERT INTO delivery_contacts (short_name, full_details) VALUES (?, ?)",
                    (short_name, full_details),
                )
        await db.commit()
