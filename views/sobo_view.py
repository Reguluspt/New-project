from __future__ import annotations

import asyncio
from datetime import datetime
import html
import io
import pandas as pd
import streamlit as st
from pathlib import Path
import zipfile

from src.database_manager import (
    delete_sobo_record,
    get_all_sobo_records,
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
        return "0g"
    total_hours = int(seconds // 3600)
    days = total_hours // 24
    hours = total_hours % 24
    if days > 0:
        return f"{days} ngày {hours}g"
    return f"{hours}g"

def collect_existing_paths(value: object) -> list[Path]:
    paths = []
    for item in str(value or "").splitlines():
        raw_path = item.strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        if path.exists() and path.is_file():
            paths.append(path)
    return paths

def build_gcn_download(paths: list[Path]) -> tuple[bytes, str, str] | None:
    if not paths:
        return None
    if len(paths) == 1:
        path = paths[0]
        return path.read_bytes(), path.name, "application/octet-stream"

    buffer = io.BytesIO()
    used_names: set[str] = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, path in enumerate(paths, 1):
            arcname = path.name
            if arcname in used_names:
                arcname = f"{path.stem}_{index}{path.suffix}"
            used_names.add(arcname)
            archive.write(path, arcname=arcname)
    return buffer.getvalue(), "sobo_gcn.zip", "application/zip"

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
            so_thua = r.get('so_thua') or ''
            so_to = r.get('so_to') or ''
            dia_chi = r.get('dia_chi') or ''
            parts = []
            if so_thua:
                parts.append(f"Thửa: {so_thua}")
            if so_to:
                parts.append(f"Tờ: {so_to}")
            prefix = ", ".join(parts)
            if prefix and dia_chi:
                asset_info = f"🏠 {prefix}; {dia_chi}"
            elif dia_chi:
                asset_info = f"🏠 {dia_chi}"
            else:
                asset_info = f"🏠 {prefix}" if prefix else "🏠"

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
            "File GCN": r.get("attachment_paths") or "",
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

    # 7. Render record cards (editable for admins, read-only for guests)
    st.markdown("**Danh sách chi tiết yêu cầu Sơ bộ**")
    st.markdown(
        """
        <style>
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-color: var(--app-outline-soft);
                box-shadow: var(--app-shadow-soft);
                background: #ffffff;
            }
            .sobo-card-muted {
                color: var(--app-muted);
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }
            .sobo-card-title {
                color: var(--app-text);
                font-size: 15px;
                font-weight: 700;
                line-height: 1.35;
            }
            .sobo-card-value {
                color: var(--app-text);
                font-size: 14px;
                line-height: 1.45;
                word-break: break-word;
            }
            .sobo-status-pill {
                display: inline-flex;
                align-items: center;
                padding: 6px 10px;
                border-radius: 999px;
                font-size: 13px;
                font-weight: 700;
                border: 1px solid transparent;
            }
            .sobo-status-pending {
                color: #b91c1c;
                background: #fef2f2;
                border-color: #fecaca;
            }
            .sobo-status-responded {
                color: #047857;
                background: #ecfdf5;
                border-color: #a7f3d0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    status_label_by_raw = {
        "PENDING": "🔴 Chờ phản hồi",
        "RESPONDED": "🟢 Đã phản hồi",
    }
    def safe_display(value: object) -> str:
        if value is None or pd.isna(value):
            return ""
        return html.escape(str(value))

    if is_guest:
        st.caption("Chế độ xem (chỉ đọc) dành cho tài khoản Khách.")
    else:
        st.caption("Trạng thái được cập nhật tự động khi hệ thống nhận mail phản hồi.")

    for _, row in df.iterrows():
        record_id = int(row["ID"])
        raw_status = str(row["_raw_status"] or "PENDING")
        status_label = status_label_by_raw.get(raw_status, status_label_by_raw["PENDING"])
        status_class = "sobo-status-responded" if raw_status == "RESPONDED" else "sobo-status-pending"

        with st.container(border=True):
            sent_at = safe_display(row["Ngày gửi"])
            asset_text = safe_display(row["Tài sản"])
            source_text = safe_display(row["Nguồn khách"])
            recipient_text = safe_display(row["Người nhận"])
            duration_text = safe_display(row["Thời gian"])
            subject_text = safe_display(row["Tiêu đề mail"] or "-")
            map_link = "" if pd.isna(row["Bản đồ"]) else str(row["Bản đồ"] or "").strip()
            gcn_paths = collect_existing_paths(row.get("File GCN"))
            gcn_download = build_gcn_download(gcn_paths)

            card_cols = st.columns([3.2, 1.2, 1.4, 0.8])
            with card_cols[0]:
                st.markdown('<div class="sobo-card-muted">Mã hồ sơ / ngày gửi</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sobo-card-value"><b>#{record_id}</b> · {sent_at}</div>', unsafe_allow_html=True)
                st.markdown('<div class="sobo-card-muted" style="margin-top:12px;">Tiêu đề mail</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sobo-card-value">{subject_text}</div>', unsafe_allow_html=True)
                st.markdown('<div class="sobo-card-muted" style="margin-top:12px;">Tài sản</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sobo-card-title">{asset_text}</div>', unsafe_allow_html=True)
                st.markdown('<div class="sobo-card-muted" style="margin-top:12px;">Nguồn / người nhận</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="sobo-card-value"><b>{source_text}</b><br>{recipient_text}</div>',
                    unsafe_allow_html=True,
                )
            with card_cols[1]:
                st.markdown('<div class="sobo-card-muted">Trạng thái</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<span class="sobo-status-pill {status_class}">{status_label}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="sobo-card-muted" style="margin-top:14px;">Thời gian</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sobo-card-value">{duration_text}</div>', unsafe_allow_html=True)
            with card_cols[2]:
                st.markdown('<div class="sobo-card-muted" style="margin-top:52px;">Bản đồ</div>', unsafe_allow_html=True)
                if map_link:
                    st.link_button("Mở bản đồ", map_link, use_container_width=True)
                else:
                    st.button("Mở bản đồ", key=f"sobo_map_disabled_{record_id}", disabled=True, use_container_width=True)
                if gcn_download:
                    data, file_name, mime = gcn_download
                    st.download_button(
                        "Tải GCN",
                        data=data,
                        file_name=file_name,
                        mime=mime,
                        key=f"sobo_gcn_download_{record_id}",
                        use_container_width=True,
                    )
                else:
                    st.button("Tải GCN", key=f"sobo_gcn_missing_{record_id}", disabled=True, use_container_width=True)
            with card_cols[3]:
                if not is_guest:
                    st.markdown('<div class="sobo-card-muted">Thao tác</div>', unsafe_allow_html=True)
                    if st.button("Xóa", key=f"sobo_delete_request_{record_id}", use_container_width=True):
                        st.session_state[f"sobo_confirm_delete_{record_id}"] = True

            if not is_guest and st.session_state.get(f"sobo_confirm_delete_{record_id}"):
                st.warning(f"Xóa hồ sơ sơ bộ #{record_id}? Thao tác này không thể hoàn tác.")
                confirm_cols = st.columns([1, 1, 4])
                with confirm_cols[0]:
                    if st.button("Xóa hồ sơ", key=f"sobo_delete_confirm_{record_id}", type="primary", use_container_width=True):
                        try:
                            loop.run_until_complete(delete_sobo_record(records_db_path, record_id))
                            st.session_state.pop(f"sobo_confirm_delete_{record_id}", None)
                            st.success(f"Đã xóa hồ sơ #{record_id}.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Lỗi khi xóa hồ sơ: {exc}")
                with confirm_cols[1]:
                    if st.button("Hủy", key=f"sobo_delete_cancel_{record_id}", use_container_width=True):
                        st.session_state.pop(f"sobo_confirm_delete_{record_id}", None)
                        st.rerun()
