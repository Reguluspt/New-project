from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from src.app_config import UNPAID_STATUS
from src.contracts import short_contract_number
from src.case_filters import (
    CUSTOMER_TYPE_LABELS,
    build_chart_data,
    build_chart_rows,
    build_filters,
    count_filtered_cases,
    format_previous_month_rows,
    get_revenue_context,
    get_unpaid_report,
    load_filter_options,
)
from src.database_store import format_money
from src.sqlite_store import (
    DEFAULT_CASE_STATUS,
    DEFAULT_PAYMENT_STATUS,
    update_case,
)


def _row_text(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def render(db_path: Path) -> None:
    """Render the revenue summary and unpaid/debt report in a dedicated tab."""
    filter_options = load_filter_options(db_path)

    st.subheader("Tổng hợp doanh thu")

    # --- Filters ---
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        selected_execution_month = st.selectbox(
            "Lọc theo tháng thực hiện",
            filter_options["execution_month"],
            key="rev_execution_month_filter",
        )
    with filter_col2:
        selected_payment_status = st.selectbox(
            "Lọc theo trạng thái thanh toán",
            filter_options["payment_status"],
            key="rev_payment_status_filter",
        )
    with filter_col3:
        selected_case_status = st.selectbox(
            "Lọc theo trạng thái hồ sơ",
            filter_options["case_status"],
            key="rev_case_status_filter",
        )
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        selected_source = st.selectbox(
            "Lọc theo nguồn/ngân hàng",
            filter_options["source"],
            key="rev_source_filter",
        )
    with adv_col2:
        selected_customer_type = st.selectbox(
            "Lọc theo loại khách hàng",
            filter_options["customer_type"],
            format_func=lambda value: CUSTOMER_TYPE_LABELS.get(value, value),
            key="rev_customer_type_filter",
        )
    with adv_col3:
        selected_business_staff = st.selectbox(
            "Lọc theo chuyên viên kinh doanh",
            filter_options["business_staff"],
            key="rev_business_staff_filter",
        )

    query = str(st.session_state.get("case_search_query", ""))
    note_query = str(st.session_state.get("case_note_query", ""))
    filters = build_filters(
        selected_execution_month=selected_execution_month,
        selected_payment_status=selected_payment_status,
        selected_case_status=selected_case_status,
        selected_source=selected_source,
        selected_customer_type=selected_customer_type,
        selected_business_staff=selected_business_staff,
    )

    total_matches = count_filtered_cases(db_path, query, filters, note_query=note_query)
    revenue_context = get_revenue_context(db_path, query, filters, note_query=note_query)
    target_month = str(revenue_context["target_month"])
    summary = revenue_context["summary"]

    # --- Revenue Metrics ---
    st.caption(
        f"Thống kê theo mốc tháng {target_month}. "
        "Doanh thu dự kiến = tổng giá trị hợp đồng; doanh thu đến hiện tại = các hồ sơ đã thanh toán."
    )
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Doanh thu dự kiến trong tháng", format_money(summary["projected_current_month"]))
    metric_col2.metric("Đã thanh toán trong tháng", format_money(summary["paid_current_month"]))
    metric_col3.metric("Chưa thanh toán trong tháng", format_money(summary["unpaid_current_month"]))
    metric_col4.metric("Doanh thu đến thời điểm hiện tại", format_money(summary["paid_to_date"]))

    # --- Revenue Chart ---
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

    # --- Unpaid / Debt Report ---
    unpaid_report = get_unpaid_report(db_path, query, filters, note_query=note_query)
    st.subheader("Báo cáo công nợ / chưa thanh toán")
    debt_col1, debt_col2 = st.columns(2)
    debt_col1.metric("Số hồ sơ chưa thanh toán", unpaid_report["count"])
    debt_col2.metric("Tổng công nợ cần thu", format_money(unpaid_report["total"]))
    if unpaid_report["rows"]:
        _render_unpaid_report_rows(db_path, unpaid_report["rows"])
    else:
        st.caption("Không có hồ sơ công nợ theo bộ lọc hiện tại.")


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
                key=f"mark_rev_unpaid_paid_{row_id}",
                width="stretch",
                disabled=row_id <= 0,
                help="Cập nhật hồ sơ này sang trạng thái Đã thanh toán",
            )
        if mark_paid:
            update_case(db_path, row_id, {"payment_status": DEFAULT_PAYMENT_STATUS})
            st.session_state["active_case_id"] = row_id
            st.rerun()
