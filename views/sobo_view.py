from __future__ import annotations

import asyncio
from datetime import datetime
import pandas as pd
import streamlit as st
from pathlib import Path

from src.database_manager import (
    get_all_sobo_records,
    update_sobo_record_status,
    resolve_records_db_path,
)

def parse_sent_time(val: str) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None

def format_duration(seconds: float) -> str:
    if seconds < 0:
        return "0 phút"
    mins = int(seconds // 60)
    hours = mins // 60
    remaining_mins = mins % 60
    if hours > 0:
        return f"{hours}g {remaining_mins}p"
    return f"{remaining_mins}p"

def render_sobo_kpi_cards(pending_count: int, responded_count: int, avg_duration_str: str, has_overdue: bool):
    overdue_style = "animation: pulse 1.5s infinite; border-color: #ff4d4d; box-shadow: 0 0 10px rgba(255, 77, 77, 0.5);" if (has_overdue and pending_count > 0) else ""
    st.markdown(
        f"""
        <style>
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.6; }}
                100% {{ opacity: 1; }}
            }}
            .sobo-kpi-grid {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 16px;
                margin: 8px 0 24px;
            }}
            .sobo-kpi-card {{
                padding: 20px 24px;
                border-radius: 12px;
                background: #ffffff;
                border: 1px solid var(--app-outline-soft);
                box-shadow: var(--app-shadow-soft);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .sobo-kpi-card:hover {{
                transform: translateY(-2px);
                box-shadow: var(--app-shadow);
            }}
            .sobo-kpi-label {{
                font-size: 11px;
                font-weight: 700;
                color: var(--app-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .sobo-kpi-value {{
                font-size: 32px;
                font-weight: 800;
                margin-top: 8px;
                color: var(--app-text);
            }}
            .sobo-kpi-card.pending {{
                border-left: 5px solid #ef4444;
                {overdue_style}
            }}
            .sobo-kpi-card.responded {{
                border-left: 5px solid #10b981;
            }}
            .sobo-kpi-card.avg-time {{
                border-left: 5px solid #3b82f6;
            }}
            .sobo-kpi-card.pending .sobo-kpi-value {{
                color: #ef4444;
            }}
            .sobo-kpi-card.responded .sobo-kpi-value {{
                color: #10b981;
            }}
            .sobo-kpi-card.avg-time .sobo-kpi-value {{
                color: #3b82f6;
            }}
        </style>
        <div class="sobo-kpi-grid">
            <div class="sobo-kpi-card pending">
                <div class="sobo-kpi-label">🔴 Chờ phản hồi</div>
                <div class="sobo-kpi-value">{pending_count}</div>
            </div>
            <div class="sobo-kpi-card responded">
                <div class="sobo-kpi-label">🟢 Đã phản hồi</div>
                <div class="sobo-kpi-value">{responded_count}</div>
            </div>
            <div class="sobo-kpi-card avg-time">
                <div class="sobo-kpi-label">⚡ Thời gian phản hồi TB</div>
                <div class="sobo-kpi-value">{avg_duration_str}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render(records_db_path: Path, is_guest: bool = False) -> None:
    st.subheader("📋 Giám sát yêu cầu Sơ bộ")
    st.caption("Theo dõi và cập nhật trạng thái phản hồi yêu cầu sơ bộ từ email phòng ban nghiệp vụ gửi qua Telegram bot.")

    # 1. Setup Event Loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 2. Controls & Force Check
    col_search, col_status, col_btn_sync, col_btn_mail = st.columns([3, 2, 1.5, 1.5])
    
    with col_search:
        search_query = st.text_input("🔍 Tìm kiếm nhanh", placeholder="Tìm theo địa chỉ, thửa, tờ, nguồn...", key="sobo_search")
    
    with col_status:
        status_filter = st.selectbox("Lọc theo trạng thái", ["Tất cả", "Chờ phản hồi", "Đã phản hồi"], key="sobo_status_filter")
        
    with col_btn_sync:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if is_guest:
            st.button("🔄 Đồng bộ Telegram", use_container_width=True, disabled=True, help="Tài khoản khách không thể đồng bộ hồ sơ Telegram.")
        else:
            if st.button("🔄 Đồng bộ Telegram", use_container_width=True, key="sobo_sync_telegram_btn"):
                with st.spinner("Đang đồng bộ hồ sơ sơ bộ từ Telegram & Hộp thư..."):
                    try:
                        from src.database_manager import sync_telegram_records_to_sobo
                        from src.mail_listener import sync_sobo_emails_from_mailbox
                        synced_db = loop.run_until_complete(sync_telegram_records_to_sobo(records_db_path))
                        synced_mail = loop.run_until_complete(sync_sobo_emails_from_mailbox(records_db_path))
                        synced = synced_db + synced_mail
                        if synced > 0:
                            st.success(f"Đồng bộ thành công! Đã thêm/cập nhật {synced} hồ sơ mới từ Telegram & Hộp thư.")
                        else:
                            st.info("Không phát hiện hồ sơ sơ bộ mới trên Telegram hoặc Hộp thư.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi đồng bộ Telegram: {exc}")

    with col_btn_mail:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if is_guest:
            st.button("🔄 Kiểm tra Mail ngay", use_container_width=True, disabled=True, help="Tài khoản khách không thể đồng bộ email thủ công.")
        else:
            if st.button("🔄 Kiểm tra Mail ngay", use_container_width=True):
                with st.spinner("Đang kiểm tra và đồng bộ mail phản hồi mới..."):
                    try:
                        from src.mail_listener import poll_unseen_once, load_mail_listener_settings
                        settings = load_mail_listener_settings()
                        processed_count = loop.run_until_complete(poll_unseen_once(settings))
                        if processed_count > 0:
                            st.success(f"Đồng bộ thành công! Tìm thấy và xử lý {processed_count} email mới.")
                        else:
                            st.info("Không phát hiện phản hồi mail mới cho hồ sơ sơ bộ.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi đồng bộ mail: {exc}")

    # 3. Load Sobo Records
    try:
        records = loop.run_until_complete(get_all_sobo_records(records_db_path))
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu sơ bộ: {e}")
        return

    if not records:
        st.info("Không tìm thấy dữ liệu yêu cầu sơ bộ nào.")
        return

    # 4. Prepare data for display
    now = datetime.now()
    formatted_rows = []
    
    pending_count = 0
    responded_count = 0
    total_reply_seconds = 0.0
    responded_with_time_count = 0
    has_overdue = False
    
    for r in records:
        status = r.get("status") or "PENDING"
        sent_time = parse_sent_time(r.get("outbound_sent_at") or r.get("created_at"))
        resp_time = parse_sent_time(r.get("responded_at"))
        
        # Calculate timers
        timer_str = "-"
        if status == "PENDING":
            pending_count += 1
            if sent_time:
                elapsed_secs = (now - sent_time).total_seconds()
                timer_str = f"⌛ {format_duration(elapsed_secs)}"
                if elapsed_secs >= 86400: # 1 day (24 hours)
                    has_overdue = True
                    timer_str = f"🔴 Trễ: {format_duration(elapsed_secs)}"
        elif status == "RESPONDED":
            responded_count += 1
            if sent_time and resp_time:
                duration_secs = (resp_time - sent_time).total_seconds()
                timer_str = f"⚡ {format_duration(duration_secs)}"
                total_reply_seconds += duration_secs
                responded_with_time_count += 1
            else:
                timer_str = "🟢 Đã xong"

        # Asset details formatting
        if r.get("asset_type") == "machinery":
            asset_info = f"⚙️ Thiết bị: {r.get('equipment_name')}"
        else:
            asset_info = f"🏠 Thửa: {r.get('so_thua') or '-'}, Tờ: {r.get('so_to') or '-'}; {r.get('dia_chi') or ''}"

        formatted_rows.append({
            "ID": r["id"],
            "Ngày gửi": sent_time.strftime("%d/%m/%Y %H:%M") if sent_time else "-",
            "Nguồn khách": r.get("source") or "",
            "Tài sản": asset_info,
            "Người nhận": r.get("email_recipient") or "",
            "Trạng thái": "🟢 Đã phản hồi" if status == "RESPONDED" else "🔴 Chờ phản hồi",
            "Thời gian": timer_str,
            "Bản đồ": r.get("link") or "",
            "Tiêu đề mail": r.get("outbound_subject") or "",
            "_raw_status": status,
        })

    # Calculate average duration
    avg_duration_str = "-"
    if responded_with_time_count > 0:
        avg_duration_str = format_duration(total_reply_seconds / responded_with_time_count)

    # 5. Render Metric Cards
    render_sobo_kpi_cards(pending_count, responded_count, avg_duration_str, has_overdue)

    # 6. Apply Filters & Search
    df = pd.DataFrame(formatted_rows)
    
    if search_query:
        q = search_query.lower().strip()
        df = df[
            df["Tài sản"].str.lower().str.contains(q, na=False) |
            df["Nguồn khách"].str.lower().str.contains(q, na=False) |
            df["Tiêu đề mail"].str.lower().str.contains(q, na=False) |
            df["Người nhận"].str.lower().str.contains(q, na=False)
        ]
        
    if status_filter == "Chờ phản hồi":
        df = df[df["Trạng thái"] == "🔴 Chờ phản hồi"]
    elif status_filter == "Đã phản hồi":
        df = df[df["Trạng thái"] == "🟢 Đã phản hồi"]

    if df.empty:
        st.warning("Không có hồ sơ nào khớp với bộ lọc tìm kiếm hiện tại.")
        return

    # 7. Render Grid (Editable for admins, read-only for guests)
    col_title, col_lock = st.columns([4, 1.5])
    with col_title:
        st.markdown("**Danh sách chi tiết yêu cầu Sơ bộ**")
    with col_lock:
        locked = st.toggle("Khóa cột", value=st.session_state.get("sobo_col_locked", True), key="sobo_col_locked")

    # Build column_config based on lock state
    _w = {
        "id": 60, "date": 130, "source": 110, "asset": 250,
        "recipient": 160, "status": 120, "time": 100, "map": 180, "subject": 250,
    } if locked else {}

    if is_guest:
        st.caption("Chế độ xem (chỉ đọc) dành cho tài khoản Khách.")
        st.dataframe(
            df[["ID", "Ngày gửi", "Nguồn khách", "Tài sản", "Người nhận", "Trạng thái", "Thời gian", "Bản đồ", "Tiêu đề mail"]],
            column_config={
                "ID": st.column_config.NumberColumn("Mã", **({"width": _w["id"]} if _w else {})),
                "Ngày gửi": st.column_config.TextColumn("Ngày gửi", **({"width": _w["date"]} if _w else {})),
                "Nguồn khách": st.column_config.TextColumn("Nguồn khách", **({"width": _w["source"]} if _w else {})),
                "Tài sản": st.column_config.TextColumn("Tài sản", **({"width": _w["asset"]} if _w else {})),
                "Người nhận": st.column_config.TextColumn("Người nhận", **({"width": _w["recipient"]} if _w else {})),
                "Trạng thái": st.column_config.TextColumn("Trạng thái", **({"width": _w["status"]} if _w else {})),
                "Thời gian": st.column_config.TextColumn("Thời gian", **({"width": _w["time"]} if _w else {})),
                "Bản đồ": st.column_config.LinkColumn("Bản đồ", **({"width": _w["map"]} if _w else {})),
                "Tiêu đề mail": st.column_config.TextColumn("Tiêu đề mail", **({"width": _w["subject"]} if _w else {})),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Mẹo: Nhấp đúp vào cột 'Trạng thái' để thay đổi trực tiếp, sau đó bấm 'Lưu thay đổi'.")
        edited_df = st.data_editor(
            df[["ID", "Ngày gửi", "Nguồn khách", "Tài sản", "Người nhận", "Trạng thái", "Thời gian", "Bản đồ", "Tiêu đề mail"]],
            column_config={
                "ID": st.column_config.NumberColumn("Mã", disabled=True, **({"width": _w["id"]} if _w else {})),
                "Ngày gửi": st.column_config.TextColumn("Ngày gửi", disabled=True, **({"width": _w["date"]} if _w else {})),
                "Nguồn khách": st.column_config.TextColumn("Nguồn khách", disabled=True, **({"width": _w["source"]} if _w else {})),
                "Tài sản": st.column_config.TextColumn("Tài sản", disabled=True, **({"width": _w["asset"]} if _w else {})),
                "Người nhận": st.column_config.TextColumn("Người nhận", disabled=True, **({"width": _w["recipient"]} if _w else {})),
                "Trạng thái": st.column_config.SelectboxColumn("Trạng thái", options=["🔴 Chờ phản hồi", "🟢 Đã phản hồi"], **({"width": _w["status"]} if _w else {})),
                "Thời gian": st.column_config.TextColumn("Thời gian", disabled=True, **({"width": _w["time"]} if _w else {})),
                "Bản đồ": st.column_config.LinkColumn("Bản đồ", disabled=True, **({"width": _w["map"]} if _w else {})),
                "Tiêu đề mail": st.column_config.TextColumn("Tiêu đề mail", disabled=True, **({"width": _w["subject"]} if _w else {})),
            },
            hide_index=True,
            use_container_width=True,
        )

        # 8. Check for Changes & Save
        # We compare edited_df with the original df
        changes_detected = False
        updates_payload = []
        
        for idx, row in edited_df.iterrows():
            orig_row = df.iloc[idx]
            new_status_str = row["Trạng thái"]
            new_status = "RESPONDED" if new_status_str == "🟢 Đã phản hồi" else "PENDING"
            
            orig_status = orig_row["_raw_status"]
            
            if new_status != orig_status:
                changes_detected = True
                updates_payload.append({
                    "id": orig_row["ID"],
                    "status": new_status,
                })

        if changes_detected:
            if st.button("💾 Lưu thay đổi", type="primary", use_container_width=True):
                with st.spinner("Đang lưu các thay đổi..."):
                    try:
                        for item in updates_payload:
                            loop.run_until_complete(update_sobo_record_status(records_db_path, item["id"], item["status"]))
                        st.success("Đã lưu các thay đổi thành công!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi khi lưu dữ liệu: {exc}")

