from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from src.app_config import UNPAID_STATUS
from src.database_store import format_money
from src.sqlite_store import (
    CANCELED_CASE_STATUS,
    DEFAULT_CASE_STATUS,
    count_cases,
    distinct_case_values,
    monthly_revenue_breakdown,
    revenue_summary,
    search_cases,
)
from src.ui_theme import render_dashboard_kpi_cards


def render(db_path: Path) -> None:
    customer_type_labels = {
        "individual": "Cá nhân",
        "organization": "Tổ chức",
    }
    execution_months = distinct_case_values(db_path, "execution_month")
    available_years = sorted({value.split("/")[1] for value in execution_months if "/" in value})
    current_year = datetime.now().strftime("%Y")
    default_year = current_year if current_year in available_years else (available_years[-1] if available_years else current_year)

    st.subheader("Dashboard")
    st.caption("Theo dõi doanh thu, doanh thu dự kiến trong tháng và công nợ theo dữ liệu hồ sơ hiện có.")

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
    with filter_col1:
        selected_year = st.selectbox(
            "Năm thống kê",
            available_years or [current_year],
            index=(available_years.index(default_year) if default_year in available_years else 0),
            key="dashboard_year",
        )
    with filter_col2:
        selected_source = st.selectbox(
            "Nguồn/ngân hàng",
            ["Tất cả"] + distinct_case_values(db_path, "source"),
            key="dashboard_source",
        )
    with filter_col3:
        selected_customer_type = st.selectbox(
            "Loại khách hàng",
            ["Tất cả"] + distinct_case_values(db_path, "customer_type"),
            format_func=lambda value: customer_type_labels.get(value, value),
            key="dashboard_customer_type",
        )
    with filter_col4:
        selected_business_staff = st.selectbox(
            "Chuyên viên kinh doanh",
            ["Tất cả"] + distinct_case_values(db_path, "business_staff"),
            key="dashboard_business_staff",
        )
    with filter_col5:
        selected_case_status = st.selectbox(
            "Trạng thái hồ sơ",
            ["Tất cả"] + distinct_case_values(db_path, "case_status"),
            key="dashboard_case_status",
        )

    source_filter = "" if selected_source == "Tất cả" else selected_source
    customer_type_filter = "" if selected_customer_type == "Tất cả" else selected_customer_type
    business_staff_filter = "" if selected_business_staff == "Tất cả" else selected_business_staff
    case_status_filter = "" if selected_case_status == "Tất cả" else selected_case_status

    monthly_rows = monthly_revenue_breakdown(
        db_path,
        year=selected_year,
        case_status=case_status_filter,
        source=source_filter,
        customer_type=customer_type_filter,
        business_staff=business_staff_filter,
    )
    month_options = [row["month"] for row in monthly_rows]
    current_month = datetime.now().strftime("%m/%Y")
    default_month = current_month if current_month in month_options else (month_options[-1] if month_options else f"01/{selected_year}")
    selected_month = st.selectbox(
        "Tháng theo dõi",
        month_options or [default_month],
        index=(month_options.index(default_month) if default_month in month_options else 0),
        key="dashboard_month",
    )

    summary = revenue_summary(
        db_path,
        target_month=selected_month,
        case_status=case_status_filter,
        source=source_filter,
        customer_type=customer_type_filter,
        business_staff=business_staff_filter,
    )

    year_projected = sum(row["projected_revenue"] for row in monthly_rows)
    year_paid = sum(row["paid_revenue"] for row in monthly_rows)
    year_unpaid = sum(row["unpaid_revenue"] for row in monthly_rows)

    render_dashboard_kpi_cards(
        year_projected=year_projected,
        year_paid=year_paid,
        year_unpaid=year_unpaid,
        month_projected=summary["projected_current_month"],
        selected_month=selected_month,
    )

    combined_chart_data = []
    month_sort = [row["month"] for row in monthly_rows]
    for row in monthly_rows:
        combined_chart_data.extend(
            [
                {"Tháng": row["month"], "Chỉ tiêu": "Doanh thu", "Giá trị": row["projected_revenue"]},
                {"Tháng": row["month"], "Chỉ tiêu": "Công nợ", "Giá trị": row["unpaid_revenue"]},
            ]
        )

    st.markdown("**Biểu đồ Doanh thu vs Công nợ hàng tháng**")
    if combined_chart_data:
        st.vega_lite_chart(
            {
                "data": {"values": combined_chart_data},
                "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
                "encoding": {
                    "x": {"field": "Tháng", "type": "ordinal", "sort": month_sort, "axis": {"labelAngle": 0}},
                    "xOffset": {"field": "Chỉ tiêu"},
                    "y": {"field": "Giá trị", "type": "quantitative"},
                    "color": {
                        "field": "Chỉ tiêu",
                        "type": "nominal",
                        "scale": {"range": ["#0052cc", "#ccdaff"]},
                    },
                    "tooltip": [
                        {"field": "Tháng", "type": "nominal"},
                        {"field": "Chỉ tiêu", "type": "nominal"},
                        {"field": "Giá trị", "type": "quantitative"},
                    ],
                },
                "height": 300,
            },
            width="stretch",
        )
    else:
        st.caption("Chưa có dữ liệu doanh thu/công nợ cho năm đang chọn.")

    monthly_table_rows = [
        {
            "Tháng": row["month"],
            "Số hồ sơ": row["case_count"],
            "Doanh thu dự kiến": format_money(row["projected_revenue"]),
            "Đã thanh toán": format_money(row["paid_revenue"]),
            "Công nợ tồn": format_money(row["unpaid_revenue"]),
        }
        for row in monthly_rows
    ]
    unpaid_count = count_cases(
        db_path,
        case_status=case_status_filter,
        payment_status=UNPAID_STATUS,
        source=source_filter,
        customer_type=customer_type_filter,
        business_staff=business_staff_filter,
    )
    unpaid_rows = search_cases(
        db_path,
        case_status=case_status_filter,
        payment_status=UNPAID_STATUS,
        source=source_filter,
        customer_type=customer_type_filter,
        business_staff=business_staff_filter,
        sort_field="execution_month",
        sort_direction="asc",
        limit=max(unpaid_count, 1),
        offset=0,
    )
    unpaid_rows = [
        row
        for row in unpaid_rows
        if str(row.get("execution_month", "")).endswith(f"/{selected_year}")
        and (row.get("case_status") or DEFAULT_CASE_STATUS) != CANCELED_CASE_STATUS
    ]
    unpaid_total = sum(float(row.get("valuation_fee_number") or 0) for row in unpaid_rows)

    bottom_col1, bottom_col2 = st.columns(2, gap="large")
    with bottom_col1:
        st.markdown("**Tổng hợp theo tháng**")
        if monthly_table_rows:
            st.dataframe(monthly_table_rows, width="stretch", hide_index=True)
        else:
            st.caption("Chưa có dữ liệu tổng hợp theo tháng.")
    with bottom_col2:
        st.markdown(f"**Báo cáo công nợ chi tiết ({selected_month})**")
        st.caption(f"Số hồ sơ chưa thanh toán: {len(unpaid_rows)} | Tổng công nợ: {format_money(unpaid_total)}")
        if unpaid_rows:
            unpaid_report_rows = [
                {
                    "Số hợp đồng": row.get("contract_number") or "",
                    "Khách hàng": row.get("customer_info") or "",
                    "Ngân hàng": row.get("source") or "",
                    "Tổng phí": format_money(row.get("valuation_fee_number")),
                    "Còn lại": format_money(row.get("valuation_fee_number")),
                    "Chuyên viên": row.get("business_staff") or "",
                }
                for row in unpaid_rows
            ]
            st.dataframe(unpaid_report_rows, width="stretch", hide_index=True)
        else:
            st.caption("Không có hồ sơ công nợ theo bộ lọc dashboard hiện tại.")
