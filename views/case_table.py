from __future__ import annotations

import asyncio
import html
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.app_config import CASE_EXPORT_DIR, CASE_FILES_DIR, CASE_TABLE_CONFIG_PATH, UNPAID_STATUS
from src.case_excel_export import export_case_rows_to_excel
from src.case_files import case_folder
from src.contracts import short_contract_number
from src.database_manager import get_db_path
from src.record_case_sync import sync_case_to_record
from src.case_filters import (
    CUSTOMER_TYPE_LABELS,
    SORT_FIELD_OPTIONS,
    build_chart_data,
    build_chart_rows,
    build_filters,
    count_filtered_cases,
    display_columns,
    export_rows_for_filters,
    export_scope_label,
    format_previous_month_rows,
    get_revenue_context,
    get_unpaid_report,
    load_filter_options,
    search_page,
)
from src.case_table_preferences import load_column_widths, save_column_widths
from src.database_store import format_money
from src.sqlite_store import (
    CANCELED_CASE_STATUS,
    DEFAULT_CASE_STATUS,
    DEFAULT_PAYMENT_STATUS,
    get_case,
    update_case,
)
from views.case_dialogs import open_case_edit_dialog


def _row_text(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _next_payment_status(row: dict[str, object]) -> tuple[str, str]:
    current = row.get("payment_status") or DEFAULT_PAYMENT_STATUS
    if current == DEFAULT_PAYMENT_STATUS:
        return UNPAID_STATUS, UNPAID_STATUS
    return DEFAULT_PAYMENT_STATUS, DEFAULT_PAYMENT_STATUS


def _next_case_status(status: object) -> tuple[str, str]:
    current = _row_text(status, DEFAULT_CASE_STATUS)
    if current == DEFAULT_CASE_STATUS:
        return "Hoàn thành", "Hoàn thành"
    if current == "Hoàn thành":
        return CANCELED_CASE_STATUS, CANCELED_CASE_STATUS
    return DEFAULT_CASE_STATUS, DEFAULT_CASE_STATUS


def _payment_badge_kind(status: object) -> str:
    text = _row_text(status, DEFAULT_PAYMENT_STATUS)
    if text == DEFAULT_PAYMENT_STATUS:
        return "paid"
    if text == UNPAID_STATUS:
        return "unpaid"
    return "neutral"


def _case_badge_kind(status: object) -> str:
    text = _row_text(status, DEFAULT_CASE_STATUS)
    if text == CANCELED_CASE_STATUS:
        return "canceled"
    if text == DEFAULT_CASE_STATUS:
        return "active"
    return "neutral"


def _state_choice(key: str, options: list[str], fallback: str | None = None) -> str:
    if not options:
        return fallback or ""
    value = st.session_state.get(key, fallback or options[0])
    if value not in options:
        value = fallback or options[0]
        st.session_state[key] = value
    return str(value)


CASE_GRID_COLUMNS = [
    ("id", "ID / Tháng", 0.7),
    ("contract", "Số HĐ / Nguồn", 1.05),
    ("customer", "Khách hàng", 1.45),
    ("citizen", "CCCD", 0.85),
    ("asset", "Tài sản", 1.05),
    ("fee", "Phí", 0.85),
    ("payment", "Thanh toán", 0.9),
    ("status", "Trạng thái", 0.85),
    ("note", "Ghi chú", 1.25),
    ("view", "Xem", 0.2),
    ("edit", "Sửa", 0.2),
]


def _case_grid_widths() -> list[float]:
    return [
        float(st.session_state.get(f"case_col_width_{key}", default))
        for key, _label, default in CASE_GRID_COLUMNS
    ]


def _case_grid_width_defaults() -> dict[str, float]:
    return {key: float(default) for key, _label, default in CASE_GRID_COLUMNS}


def _ensure_case_grid_width_state() -> None:
    saved_widths = load_column_widths(CASE_TABLE_CONFIG_PATH, _case_grid_width_defaults())
    for key, value in saved_widths.items():
        st.session_state.setdefault(f"case_col_width_{key}", value)


def _grid_template(widths: list[float]) -> str:
    return " ".join(f"{width:g}fr" for width in widths)


def _render_column_width_controls() -> list[float]:
    _ensure_case_grid_width_state()
    with st.expander("Điều chỉnh độ rộng cột", expanded=False):
        st.caption("Kéo thanh trượt để đổi tỷ lệ chiều rộng cột trong bảng danh mục hồ sơ.")
        control_cols = st.columns(4)
        for index, (key, label, default) in enumerate(CASE_GRID_COLUMNS):
            with control_cols[index % len(control_cols)]:
                st.slider(
                    label,
                    min_value=0.15,
                    max_value=2.5,
                    value=float(st.session_state.get(f"case_col_width_{key}", default)),
                    step=0.05,
                    key=f"case_col_width_{key}",
                )
    widths_by_key = {
        key: float(st.session_state.get(f"case_col_width_{key}", default))
        for key, _label, default in CASE_GRID_COLUMNS
    }
    save_column_widths(CASE_TABLE_CONFIG_PATH, widths_by_key)
    return [widths_by_key[key] for key, _label, _default in CASE_GRID_COLUMNS]


def _render_case_grid_styles(widths: list[float]) -> None:
    grid_template = _grid_template(widths)
    st.markdown(
        """
        <style>
            .case-grid-header {
                display: grid;
                grid-template-columns: __GRID_TEMPLATE__;
                gap: 8px;
                align-items: center;
                min-width: 1320px;
                padding: 10px 12px;
                border: 1px solid #dbe3f3;
                border-radius: 8px;
                background: #eef3ff;
                color: #394762;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }
            .case-grid-cell-main {
                font-weight: 700;
                color: #0f2d5c;
            }
            .case-grid-cell-sub {
                color: #667085;
                font-size: 12px;
                line-height: 1.35;
                margin-top: 2px;
            }
            .case-grid-scroll {
                overflow-x: auto;
                padding-bottom: 4px;
            }
            div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
                min-height: 34px;
                padding-left: 0.35rem;
                padding-right: 0.35rem;
            }
            .case-grid-action-header {
                text-align: center;
            }
            .case-status-badge {
                display: inline-flex;
                align-items: center;
                min-height: 24px;
                padding: 2px 9px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                line-height: 18px;
                white-space: nowrap;
                border: 1px solid transparent;
            }
            .case-status-badge-paid {
                background: #e7f8ef;
                color: #047857;
                border-color: #a7f3d0;
            }
            .case-status-badge-unpaid {
                background: #fff7ed;
                color: #c2410c;
                border-color: #fed7aa;
            }
            .case-status-badge-active {
                background: #eaf1ff;
                color: #1d4ed8;
                border-color: #bfdbfe;
            }
            .case-status-badge-canceled {
                background: #fff1f2;
                color: #be123c;
                border-color: #fecdd3;
            }
            .case-status-badge-neutral {
                background: #f1f5f9;
                color: #475569;
                border-color: #e2e8f0;
            }
        </style>
        """.replace("__GRID_TEMPLATE__", grid_template),
        unsafe_allow_html=True,
    )


def _render_case_row(
    *,
    db_path: Path,
    row: dict[str, object],
    active_case_id: int | None,
    widths: list[float],
) -> None:
    row_id = int(row["id"])
    row_status = row.get("case_status") or DEFAULT_CASE_STATUS
    payment_label, next_payment = _next_payment_status(row)
    next_case_status_label, next_case_status = _next_case_status(row_status)
    is_active = row_id == active_case_id
    is_canceled = row_status == CANCELED_CASE_STATUS

    with st.container(border=True):
        cols = st.columns(widths)
        cols[0].markdown(f"**#{row_id}**")
        cols[0].caption(_row_text(row.get("execution_month"), "Chưa có tháng"))
        cols[1].markdown(f"**{short_contract_number(row.get('contract_number'), fallback='Chưa có số HĐ')}**")
        cols[1].caption(_row_text(row.get("source"), "Chưa có nguồn"))
        cols[2].markdown(f"**{_row_text(row.get('customer_info'), 'Chưa có khách hàng')}**")
        cols[2].caption(CUSTOMER_TYPE_LABELS.get(str(row.get("customer_type") or "individual"), "Cá nhân"))
        cols[3].write(_row_text(row.get("citizen_id"), "-"))
        cols[4].write(_row_text(row.get("asset_type") or row.get("asset_description"), "Chưa có tài sản"))
        cols[5].markdown(f"**{format_money(row.get('valuation_fee_number'))}**")
        if cols[6].button(
            _row_text(row.get("payment_status"), DEFAULT_PAYMENT_STATUS),
            key=f"payment_status_case_{row_id}",
            width="content",
            disabled=is_canceled,
            help=f"Đổi sang {payment_label}",
        ):
            update_case(db_path, row_id, {"payment_status": next_payment})
            st.session_state["active_case_id"] = row_id
            st.rerun()
        if cols[7].button(
            _row_text(row_status, DEFAULT_CASE_STATUS),
            key=f"case_status_case_{row_id}",
            width="content",
            help=f"Đổi sang {next_case_status_label}",
        ):
            update_case(db_path, row_id, {"case_status": next_case_status, "cancel_reason": ""})
            asyncio.run(sync_case_to_record(get_db_path(), db_path, row_id))
            st.session_state["active_case_id"] = row_id
            st.rerun()
        if is_active:
            cols[7].caption("Đang chọn")
        cols[8].write(_row_text(row.get("personal_note"), "-"))

        if cols[9].button(
            " ",
            key=f"select_case_{row_id}",
            width="content",
            icon=":material/visibility:",
            help="Chọn hồ sơ này để xem và xuất Word/PDF/ZIP",
        ):
            st.session_state["active_case_id"] = row_id
            st.session_state["case_documents_dialog_open"] = True
            st.rerun()
        if cols[10].button(
            " ",
            key=f"edit_case_{row_id}",
            width="content",
            icon=":material/edit:",
            help="Mở popup sửa hồ sơ",
        ):
            st.session_state["active_case_id"] = row_id
            open_case_edit_dialog(db_path, row_id)


def _render_case_grid(db_path: Path, rows: list[dict[str, object]], active_case_id: int | None, widths: list[float]) -> None:
    _render_case_grid_styles(widths)
    st.markdown("**Danh mục hồ sơ và thao tác nhanh**")
    st.caption("Bấm trực tiếp vào trạng thái thanh toán hoặc trạng thái hồ sơ để đổi nhanh. Bấm icon mắt để chọn hồ sơ cho khung xem/xuất tài liệu bên dưới.")
    header_cells = "\n".join(
        f'                <div class="case-grid-action-header">{html.escape(label)}</div>'
        if key in {"view", "edit"}
        else f"                <div>{html.escape(label)}</div>"
        for key, label, _default in CASE_GRID_COLUMNS
    )
    st.markdown(
        f"""
        <div class="case-grid-scroll">
            <div class="case-grid-header">
{header_cells}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for row in rows:
        _render_case_row(db_path=db_path, row=row, active_case_id=active_case_id, widths=widths)


def _render_unpaid_report_rows(db_path: Path, rows: list[dict[str, object]]) -> None:
    st.caption("Danh sách hồ sơ chưa thanh toán")
    column_widths = [0.65, 1.1, 2.25, 0.85, 1.55, 0.85, 1.75, 1.35, 0.9]
    headers = [
        "Tháng",
        "Số hợp đồng",
        "Khách hàng",
        "Loại KH",
        "Nguồn/ngân hàng",
        "Phí",
        "Địa chỉ",
        "Ghi chú",
        "Thao tác",
    ]
    header = st.columns(column_widths)
    for index, label in enumerate(headers):
        header[index].markdown(f"**{label}**")
    for row in rows:
        row_id = int(row.get("_id") or 0)
        with st.container(border=True):
            cols = st.columns(column_widths)
            cols[0].write(_row_text(row.get("Tháng thực hiện")))
            cols[1].write(short_contract_number(row.get("Số hợp đồng"), fallback="-"))
            cols[2].write(_row_text(row.get("Khách hàng")))
            cols[3].write(_row_text(row.get("Loại khách hàng")))
            cols[4].write(_row_text(row.get("Nguồn/ngân hàng")))
            cols[5].write(_row_text(row.get("Phí thẩm định")))
            cols[6].write(_row_text(row.get("Địa chỉ khách hàng")))
            cols[7].write(_row_text(row.get("Ghi chú cá nhân")))
            mark_paid = cols[8].button(
                "Đã thanh toán",
                key=f"mark_unpaid_report_paid_{row_id}",
                width="stretch",
                disabled=row_id <= 0,
                help="Cập nhật hồ sơ này sang trạng thái Đã thanh toán",
            )
        if mark_paid:
            update_case(db_path, row_id, {"payment_status": DEFAULT_PAYMENT_STATUS})
            st.session_state["active_case_id"] = row_id
            st.rerun()


def render(db_path: Path) -> dict[str, object] | None:
    filter_options = load_filter_options(db_path)
    query = str(st.session_state.get("case_search_query", ""))
    note_query = str(st.session_state.get("case_note_query", ""))
    selected_execution_month = _state_choice("case_execution_month_filter", filter_options["execution_month"])
    selected_payment_status = _state_choice("case_payment_status_filter", filter_options["payment_status"])
    selected_case_status = _state_choice("case_status_filter", filter_options["case_status"])
    selected_source = _state_choice("case_source_filter", filter_options["source"])
    selected_customer_type = _state_choice("case_customer_type_filter", filter_options["customer_type"])
    selected_business_staff = _state_choice("case_business_staff_filter", filter_options["business_staff"])

    filters = build_filters(
        selected_execution_month=selected_execution_month,
        selected_payment_status=selected_payment_status,
        selected_case_status=selected_case_status,
        selected_source=selected_source,
        selected_customer_type=selected_customer_type,
        selected_business_staff=selected_business_staff,
    )
    sort_label = _state_choice("case_sort_field_v2", list(SORT_FIELD_OPTIONS.keys()), "Tháng thực hiện")
    sort_direction_label = _state_choice("case_sort_direction_v2", ["Giảm dần", "Tăng dần"])
    sort_field = SORT_FIELD_OPTIONS[sort_label]
    sort_direction = "desc" if sort_direction_label == "Giảm dần" else "asc"
    total_matches = count_filtered_cases(db_path, query, filters, note_query=note_query)
    revenue_context = get_revenue_context(db_path, query, filters, note_query=note_query)
    target_month = str(revenue_context["target_month"])
    summary = revenue_context["summary"]
    st.subheader("Tổng hợp doanh thu")
    st.caption(
        f"Thống kê theo mốc tháng {target_month}. "
        "Doanh thu dự kiến = tổng giá trị hợp đồng; doanh thu đến hiện tại = các hồ sơ đã thanh toán."
    )
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Doanh thu dự kiến trong tháng", format_money(summary["projected_current_month"]))
    metric_col2.metric("Đã thanh toán trong tháng", format_money(summary["paid_current_month"]))
    metric_col3.metric("Chưa thanh toán trong tháng", format_money(summary["unpaid_current_month"]))
    metric_col4.metric("Doanh thu đến thời điểm hiện tại", format_money(summary["paid_to_date"]))
    chart_rows = build_chart_rows(summary, total_matches)
    chart_data = build_chart_data(chart_rows)

    st.caption("Biểu đồ doanh thu theo tháng")
    st.vega_lite_chart(
        {
            "data": {"values": chart_data},
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {"field": "Tháng", "type": "ordinal", "sort": [row["Tháng"] for row in chart_rows]},
                "y": {"field": "Giá trị", "type": "quantitative"},
                "color": {"field": "Chỉ tiêu", "type": "nominal"},
                "tooltip": [
                    {"field": "Tháng", "type": "nominal"},
                    {"field": "Chỉ tiêu", "type": "nominal"},
                    {"field": "Giá trị", "type": "quantitative"},
                ],
            },
            "height": 340,
        },
        width="stretch",
    )
    if summary["previous_months"]:
        previous_month_rows = format_previous_month_rows(summary)
        st.caption("Thống kê các tháng trước")
        st.dataframe(previous_month_rows, width="stretch", hide_index=True)
    else:
        st.caption("Chưa có dữ liệu các tháng trước theo bộ lọc hiện tại.")

    unpaid_report = get_unpaid_report(db_path, query, filters, note_query=note_query)
    st.subheader("Báo cáo công nợ / chưa thanh toán")
    debt_col1, debt_col2 = st.columns(2)
    debt_col1.metric("Số hồ sơ chưa thanh toán", unpaid_report["count"])
    debt_col2.metric("Tổng công nợ cần thu", format_money(unpaid_report["total"]))
    if unpaid_report["rows"]:
        _render_unpaid_report_rows(db_path, unpaid_report["rows"])
    else:
        st.caption("Không có hồ sơ công nợ theo bộ lọc hiện tại.")

    st.subheader("Tìm kiếm hồ sơ")
    search_col, note_search_col = st.columns(2)
    with search_col:
        query = st.text_input(
            "Tìm kiếm động",
            placeholder="Tên khách hàng, số hợp đồng, CCCD, địa chỉ, ngân hàng...",
            key="case_search_query",
            help="Tự lọc khi nhập, không cần bấm nút tìm kiếm.",
        )
    with note_search_col:
        note_query = st.text_input(
            "Tìm trong ghi chú cá nhân",
            placeholder="Nhập nội dung cần tìm trong cột ghi chú...",
            key="case_note_query",
            help="Chỉ tìm trong cột Ghi chú cá nhân.",
        )
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        selected_execution_month = st.selectbox(
            "Lọc theo tháng thực hiện",
            filter_options["execution_month"],
            key="case_execution_month_filter",
        )
    with filter_col2:
        selected_payment_status = st.selectbox(
            "Lọc theo trạng thái thanh toán",
            filter_options["payment_status"],
            key="case_payment_status_filter",
        )
    with filter_col3:
        selected_case_status = st.selectbox(
            "Lọc theo trạng thái hồ sơ",
            filter_options["case_status"],
            key="case_status_filter",
        )
    shortcut_col1, shortcut_col2 = st.columns([1, 3])
    with shortcut_col1:
        if st.button("Chỉ xem hồ sơ Hủy", key="case_shortcut_canceled", width="stretch"):
            st.session_state["case_status_filter"] = CANCELED_CASE_STATUS
            st.rerun()
    with shortcut_col2:
        st.caption("Nút shortcut này đặt bộ lọc trạng thái hồ sơ về `Hủy` để rà soát nhanh các hồ sơ đã hủy.")
    advanced_col1, advanced_col2, advanced_col3 = st.columns(3)
    with advanced_col1:
        selected_source = st.selectbox(
            "Lọc theo nguồn/ngân hàng",
            filter_options["source"],
            key="case_source_filter",
        )
    with advanced_col2:
        selected_customer_type = st.selectbox(
            "Lọc theo loại khách hàng",
            filter_options["customer_type"],
            format_func=lambda value: CUSTOMER_TYPE_LABELS.get(value, value),
            key="case_customer_type_filter",
        )
    with advanced_col3:
        selected_business_staff = st.selectbox(
            "Lọc theo chuyên viên kinh doanh",
            filter_options["business_staff"],
            key="case_business_staff_filter",
        )
    filters = build_filters(
        selected_execution_month=selected_execution_month,
        selected_payment_status=selected_payment_status,
        selected_case_status=selected_case_status,
        selected_source=selected_source,
        selected_customer_type=selected_customer_type,
        selected_business_staff=selected_business_staff,
    )
    sort_col1, sort_col2 = st.columns(2)
    with sort_col1:
        sort_label = st.selectbox(
            "Sắp xếp theo",
            list(SORT_FIELD_OPTIONS.keys()),
            index=list(SORT_FIELD_OPTIONS.keys()).index(sort_label),
            key="case_sort_field_v2",
        )
    with sort_col2:
        sort_direction_label = st.radio(
            "Chiều sắp xếp",
            ["Giảm dần", "Tăng dần"],
            horizontal=True,
            index=0 if sort_direction_label == "Giảm dần" else 1,
            key="case_sort_direction_v2",
        )
    sort_field = SORT_FIELD_OPTIONS[sort_label]
    sort_direction = "desc" if sort_direction_label == "Giảm dần" else "asc"
    total_matches = count_filtered_cases(db_path, query, filters, note_query=note_query)
    page_state_signature = (
        query,
        note_query,
        filters["execution_month"],
        filters["payment_status"],
        filters["case_status"],
        filters["source"],
        filters["customer_type"],
        filters["business_staff"],
        sort_field,
        sort_direction,
    )
    if st.session_state.get("case_page_signature") != page_state_signature:
        st.session_state["case_page_signature"] = page_state_signature
        st.session_state["case_page_number"] = 1

    page_col, size_col, info_col = st.columns([1, 1, 2])
    with page_col:
        page_size = st.selectbox("Số dòng/trang", [50, 100, 200, 500], index=1, key="case_page_size")
    total_pages = max(1, (total_matches + page_size - 1) // page_size)
    with size_col:
        current_page = min(int(st.session_state.get("case_page_number", 1)), total_pages)
        st.session_state["case_page_number"] = current_page
        page_number = st.number_input(
            "Trang",
            min_value=1,
            max_value=total_pages,
            step=1,
            key="case_page_number",
        )
    with info_col:
        st.caption(f"Tổng hồ sơ phù hợp: {total_matches}")

    rows = search_page(
        db_path,
        query,
        filters,
        note_query=note_query,
        sort_field=sort_field,
        sort_direction=sort_direction,
        page_size=page_size,
        page_number=int(page_number),
    )
    if not rows:
        st.info("Không tìm thấy hồ sơ phù hợp.")
        return None

    selected_ids = [int(row["id"]) for row in rows]
    active_case_id = st.session_state.get("active_case_id")
    active_case_id = int(active_case_id) if active_case_id in selected_ids else selected_ids[0]
    st.session_state["active_case_id"] = active_case_id

    all_columns = display_columns(rows)
    default_columns = st.session_state.get("case_visible_columns", all_columns)
    valid_default_columns = [column for column in default_columns if column in all_columns] or all_columns
    visible_columns = st.multiselect(
        "Chọn cột xuất Excel",
        all_columns,
        default=valid_default_columns,
        key="case_visible_columns",
    )
    if not visible_columns:
        st.warning("Cần chọn ít nhất một cột để xuất Excel.")
        visible_columns = all_columns

    st.caption(f"Đang hiển thị trang {int(page_number)}/{total_pages}")
    widths = _render_column_width_controls()
    _render_case_grid(db_path, rows, active_case_id, widths)

    batch_options = {
        f"#{row['id']} | {short_contract_number(row.get('contract_number'), fallback='Chưa có số HĐ')} | {row.get('customer_info') or 'Chưa có khách hàng'}": row["id"]
        for row in rows
    }
    st.markdown("**Batch action trên trang hiện tại**")
    selected_batch_labels = st.multiselect(
        "Chọn nhiều hồ sơ",
        list(batch_options.keys()),
        key="case_batch_selected_rows",
    )
    selected_batch_ids = [batch_options[label] for label in selected_batch_labels]
    batch_col1, batch_col2 = st.columns(2)
    with batch_col1:
        if st.button("Hủy nhiều hồ sơ", key="batch_cancel_cases", width="stretch", icon=":material/block:", disabled=not selected_batch_ids):
            for case_id in selected_batch_ids:
                update_case(db_path, int(case_id), {"case_status": CANCELED_CASE_STATUS, "cancel_reason": ""})
                asyncio.run(sync_case_to_record(get_db_path(), db_path, int(case_id)))
            st.success(f"Đã hủy {len(selected_batch_ids)} hồ sơ.")
            st.rerun()
    with batch_col2:
        if st.button("Khôi phục nhiều hồ sơ", key="batch_restore_cases", width="stretch", icon=":material/undo:", disabled=not selected_batch_ids):
            for case_id in selected_batch_ids:
                update_case(db_path, int(case_id), {"case_status": DEFAULT_CASE_STATUS, "cancel_reason": ""})
                asyncio.run(sync_case_to_record(get_db_path(), db_path, int(case_id)))
            st.success(f"Đã khôi phục {len(selected_batch_ids)} hồ sơ.")
            st.rerun()

    export_count = count_filtered_cases(db_path, query, filters, note_query=note_query)
    export_filtered_rows = export_rows_for_filters(
        db_path,
        query,
        filters,
        note_query=note_query,
        visible_columns=visible_columns,
        sort_field=sort_field,
        sort_direction=sort_direction,
        export_count=export_count,
    )
    export_filename = f"ho_so_loc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_path = CASE_EXPORT_DIR / export_filename
    export_case_rows_to_excel(export_filtered_rows, visible_columns, export_path)
    export_label = export_scope_label(query, filters)
    st.download_button(
        "Xuất Excel theo bộ lọc hiện tại",
        data=export_path.read_bytes(),
        file_name=export_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key=f"download_case_export_{hash((query, note_query, filters['execution_month'], filters['payment_status'], tuple(visible_columns), sort_field, sort_direction, total_matches))}",
    )
    st.caption(f"File xuất: {export_path}")
    st.caption(f"Phạm vi xuất: {export_label} | Tổng dòng: {len(export_filtered_rows)}")

    selected_id = int(st.session_state["active_case_id"])
    case = get_case(db_path, selected_id)
    if not case:
        st.warning("Hồ sơ đã chọn không còn tồn tại.")
        return None

    refreshed_case = get_case(db_path, selected_id)
    effective_case_folder = None
    if refreshed_case:
        effective_case_folder = Path(
            refreshed_case.get("case_folder")
            or case_folder(
                CASE_FILES_DIR,
                case_id=int(refreshed_case["id"]),
                contract_number=refreshed_case.get("contract_number") or "",
                customer_name=refreshed_case.get("customer_info") or "",
            )
        )

    return {
        "selected_id": selected_id,
        "case": case,
        "refreshed_case": refreshed_case,
        "effective_case_folder": effective_case_folder,
    }
