from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.app_config import UNPAID_STATUS
from src.contracts import short_contract_number
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


def _money_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _format_million(value: float) -> str:
    return f"{value / 1_000_000:,.0f}".replace(",", ".")


def _bank_system_name(source: object) -> str:
    text = str(source or "").strip()
    if not text:
        return "Khác"
    return text.split(" - ", 1)[0].strip() or text


def _render_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
            .dashboard-title {
                margin: 0;
                color: var(--app-text);
                font-size: 32px;
                line-height: 38px;
                font-weight: 760;
            }
            .dashboard-caption {
                margin: 4px 0 14px;
                color: var(--app-muted);
                font-size: 13px;
                line-height: 1.45;
            }
            .dashboard-section-title {
                margin: 0 0 10px;
                color: var(--app-text);
                font-size: 18px;
                line-height: 24px;
                font-weight: 750;
            }
            .dashboard-panel {
                padding: 12px;
                border: 1px solid var(--app-outline);
                border-radius: 12px;
                background: #fff;
                overflow: hidden;
            }
            .dashboard-panel + .dashboard-panel {
                margin-top: 14px;
            }
            .dashboard-mini-caption {
                margin: -4px 0 10px;
                color: var(--app-muted);
                font-size: 12px;
                line-height: 1.35;
            }
            .dashboard-table-wrap {
                width: 100%;
                overflow: hidden;
                border: 1px solid var(--app-outline-soft);
                border-radius: 10px;
                background: #fff;
            }
            .dashboard-table {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                font-size: 13px;
            }
            .dashboard-table th {
                height: 44px;
                padding: 0 10px;
                background: #f8fafc;
                border-right: 1px solid var(--app-outline-soft);
                border-bottom: 1px solid var(--app-outline-soft);
                color: #64748b;
                font-weight: 700;
                text-align: center;
            }
            .dashboard-table th:last-child,
            .dashboard-table td:last-child {
                border-right: 0;
            }
            .dashboard-table td {
                height: 43px;
                padding: 7px 10px;
                border-right: 1px solid var(--app-outline-soft);
                border-bottom: 1px solid var(--app-outline-soft);
                color: var(--app-text);
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }
            .dashboard-table tr:last-child td {
                border-bottom: 0;
            }
            .dashboard-table .right {
                text-align: right;
                font-variant-numeric: tabular-nums;
            }
            .vega-embed.has-actions {
                padding-right: 0 !important;
            }
            .vega-embed details {
                display: none !important;
            }
            .vega-embed,
            .vega-embed > div,
            .vega-embed svg {
                width: 100% !important;
                max-width: 100% !important;
            }
            .bank-donut-wrap {
                display: grid;
                grid-template-columns: 250px minmax(0, 1fr);
                align-items: center;
                gap: 18px;
                min-height: 245px;
            }
            .bank-donut {
                width: 225px;
                height: 225px;
                border-radius: 50%;
                background: var(--donut-gradient);
                position: relative;
                margin: 0 auto;
            }
            .bank-donut::after {
                content: "";
                position: absolute;
                inset: 60px;
                border-radius: 50%;
                background: #fff;
            }
            .bank-donut-center {
                position: absolute;
                inset: 0;
                z-index: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
            }
            .bank-donut-center b {
                color: var(--app-text);
                font-size: 25px;
                line-height: 1;
                font-weight: 850;
            }
            .bank-donut-center span {
                margin-top: 7px;
                color: var(--app-muted);
                font-size: 12px;
                font-weight: 700;
            }
            .bank-legend {
                display: grid;
                gap: 5px;
            }
            .bank-legend-row {
                display: grid;
                grid-template-columns: 10px minmax(0, 1fr) auto;
                align-items: center;
                gap: 7px;
                color: #334155;
                font-size: 12px;
                min-height: 20px;
            }
            .bank-legend-dot {
                width: 10px;
                height: 10px;
                border-radius: 3px;
                background: var(--legend-color);
            }
            .bank-legend-name {
                min-width: 0;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }
            .bank-legend-value {
                color: var(--app-text);
                font-weight: 760;
                font-size: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _bank_revenue_rows(
    db_path: Path,
    *,
    selected_year: str,
    case_status_filter: str,
    source_filter: str,
    customer_type_filter: str,
    business_staff_filter: str,
) -> list[dict[str, object]]:
    total_count = count_cases(
        db_path,
        case_status=case_status_filter,
        source=source_filter,
        customer_type=customer_type_filter,
        business_staff=business_staff_filter,
    )
    rows = search_cases(
        db_path,
        case_status=case_status_filter,
        source=source_filter,
        customer_type=customer_type_filter,
        business_staff=business_staff_filter,
        sort_field="execution_month",
        sort_direction="asc",
        limit=max(total_count, 1),
        offset=0,
    )
    totals: dict[str, float] = {}
    for row in rows:
        if not str(row.get("execution_month", "")).endswith(f"/{selected_year}"):
            continue
        if (row.get("case_status") or DEFAULT_CASE_STATUS) == CANCELED_CASE_STATUS:
            continue
        source = _bank_system_name(row.get("source"))
        totals[source] = totals.get(source, 0.0) + _money_float(row.get("valuation_fee_number"))

    sorted_rows = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    sorted_rows = sorted_rows[:10]

    total = sum(value for _name, value in sorted_rows)
    if total <= 0:
        return []
    return [
        {
            "bank": name,
            "value": value,
            "percent": round(value / total * 100, 1),
        }
        for name, value in sorted_rows
    ]


def render(db_path: Path) -> None:
    _render_dashboard_styles()
    customer_type_labels = {
        "individual": "Cá nhân",
        "organization": "Tổ chức",
    }
    execution_months = distinct_case_values(db_path, "execution_month")
    available_years = sorted({value.split("/")[1] for value in execution_months if "/" in value})
    current_year = datetime.now().strftime("%Y")
    default_year = current_year if current_year in available_years else (available_years[-1] if available_years else current_year)

    st.markdown('<h1 class="dashboard-title">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-caption">Theo dõi doanh thu dự kiến, thanh toán, công nợ và tỷ lệ doanh thu theo hệ thống ngân hàng.</div>',
        unsafe_allow_html=True,
    )

    filter_cols = st.columns(6)
    with filter_cols[0]:
        selected_year = st.selectbox(
            "Năm thống kê",
            available_years or [current_year],
            index=(available_years.index(default_year) if default_year in available_years else 0),
            key="dashboard_year",
        )
    with filter_cols[1]:
        selected_source = st.selectbox(
            "Nguồn/ngân hàng",
            ["Tất cả"] + distinct_case_values(db_path, "source"),
            key="dashboard_source",
        )
    with filter_cols[2]:
        selected_customer_type = st.selectbox(
            "Loại khách hàng",
            ["Tất cả"] + distinct_case_values(db_path, "customer_type"),
            format_func=lambda value: customer_type_labels.get(value, value),
            key="dashboard_customer_type",
        )
    with filter_cols[3]:
        selected_business_staff = st.selectbox(
            "Chuyên viên kinh doanh",
            ["Tất cả"] + distinct_case_values(db_path, "business_staff"),
            key="dashboard_business_staff",
        )
    with filter_cols[4]:
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
    with filter_cols[5]:
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

    monthly_table_rows = [
        {
            "Tháng": row["month"],
            "Hồ sơ": row["case_count"],
            "Dự kiến": format_money(row["projected_revenue"]),
            "Đã thu": format_money(row["paid_revenue"]),
            "Công nợ": format_money(row["unpaid_revenue"]),
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
    unpaid_total = sum(_money_float(row.get("valuation_fee_number")) for row in unpaid_rows)

    bank_rows = _bank_revenue_rows(
        db_path,
        selected_year=selected_year,
        case_status_filter=case_status_filter,
        source_filter=source_filter,
        customer_type_filter=customer_type_filter,
        business_staff_filter=business_staff_filter,
    )

    chart_col, report_col = st.columns([1, 1], gap="medium")
    with chart_col:
        with st.container(border=True, height=385):
            st.markdown('<div class="dashboard-section-title">Doanh thu vs Công nợ hàng tháng</div>', unsafe_allow_html=True)
            if combined_chart_data:
                st.vega_lite_chart(
                    {
                        "data": {"values": combined_chart_data},
                        "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
                        "encoding": {
                            "x": {"field": "Tháng", "type": "ordinal", "sort": month_sort, "axis": {"labelAngle": 0}},
                            "xOffset": {"field": "Chỉ tiêu"},
                            "y": {"field": "Giá trị", "type": "quantitative", "axis": {"title": "Giá trị"}},
                        "color": {
                            "field": "Chỉ tiêu",
                            "type": "nominal",
                            "scale": {"range": ["#0f6cbd", "#c7d8ff"]},
                            "legend": {"orient": "top", "direction": "horizontal", "title": None},
                        },
                            "tooltip": [
                                {"field": "Tháng", "type": "nominal"},
                                {"field": "Chỉ tiêu", "type": "nominal"},
                                {"field": "Giá trị", "type": "quantitative"},
                            ],
                        },
                        "height": 292,
                    },
                    width="stretch",
                )
            else:
                st.caption("Chưa có dữ liệu doanh thu/công nợ cho năm đang chọn.")

        with st.container(border=True, height=330):
            st.markdown('<div class="dashboard-section-title">Tỷ lệ doanh thu theo ngân hàng</div>', unsafe_allow_html=True)
            st.markdown('<div class="dashboard-mini-caption">Tổng doanh thu dự kiến trong năm theo bộ lọc hiện tại.</div>', unsafe_allow_html=True)
            _render_bank_donut(bank_rows)

    with report_col:
        with st.container(border=True, height=385):
            st.markdown('<div class="dashboard-section-title">Tổng hợp theo tháng</div>', unsafe_allow_html=True)
            if monthly_table_rows:
                _render_dashboard_table(
                    monthly_table_rows,
                    [
                        ("Tháng", "Tháng", "16%"),
                        ("Hồ sơ", "Hồ sơ", "14%"),
                        ("Dự kiến", "Dự kiến", "24%"),
                        ("Đã thu", "Đã thu", "23%"),
                        ("Công nợ", "Công nợ", "23%"),
                    ],
                    right_align={"Hồ sơ", "Dự kiến", "Đã thu", "Công nợ"},
                )
            else:
                st.caption("Chưa có dữ liệu tổng hợp theo tháng.")

        with st.container(border=True, height=330):
            st.markdown(f'<div class="dashboard-section-title">Báo cáo công nợ chi tiết ({html.escape(selected_month)})</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="dashboard-mini-caption">Số hồ sơ chưa thanh toán: {len(unpaid_rows)} | Tổng công nợ: {format_money(unpaid_total)}</div>',
                unsafe_allow_html=True,
            )
            if unpaid_rows:
                unpaid_report_rows = [
                    {
                        "Số HĐ": short_contract_number(row.get("contract_number")),
                        "Khách hàng": row.get("customer_info") or "",
                        "Ngân hàng": row.get("source") or "",
                        "Còn lại": format_money(row.get("valuation_fee_number")),
                    }
                    for row in unpaid_rows
                ]
                _render_dashboard_table(
                    unpaid_report_rows,
                    [
                        ("Số HĐ", "Số HĐ", "16%"),
                        ("Khách hàng", "Khách hàng", "48%"),
                        ("Ngân hàng", "Ngân hàng", "22%"),
                        ("Còn lại", "Còn lại", "14%"),
                    ],
                    right_align={"Còn lại"},
                )
            else:
                st.caption("Không có hồ sơ công nợ theo bộ lọc dashboard hiện tại.")


def _render_dashboard_table(
    rows: list[dict[str, object]],
    columns: list[tuple[str, str, str]],
    *,
    right_align: set[str] | None = None,
) -> None:
    right_align = right_align or set()
    colgroup = "".join(f'<col style="width:{width}">' for _key, _label, width in columns)
    header = "".join(f"<th>{html.escape(label)}</th>" for _key, label, _width in columns)
    table_rows: list[str] = []
    for row in rows:
        cells = []
        for key, _label, _width in columns:
            value = html.escape(str(row.get(key, "") or ""))
            css_class = ' class="right"' if key in right_align else ""
            title = f' title="{value}"' if value else ""
            cells.append(f"<td{css_class}{title}>{value}</td>")
        table_rows.append(f"<tr>{''.join(cells)}</tr>")
    if not table_rows:
        table_rows.append(f'<tr><td colspan="{len(columns)}">Không có dữ liệu.</td></tr>')
    st.markdown(
        f'<div class="dashboard-table-wrap"><table class="dashboard-table"><colgroup>{colgroup}</colgroup>'
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_bank_donut(bank_rows: list[dict[str, object]]) -> None:
    colors = [
        "#0f6cbd",
        "#2aa0a4",
        "#8ab8ff",
        "#ffcc4d",
        "#7c3aed",
        "#14b8a6",
        "#f97316",
        "#64748b",
        "#db2777",
        "#84cc16",
    ]
    total = sum(float(row["value"]) for row in bank_rows)
    if total <= 0:
        st.caption("Chưa có dữ liệu doanh thu theo ngân hàng trong năm đang chọn.")
        return

    cursor = 0.0
    stops: list[str] = []
    legend_rows: list[str] = []
    for index, row in enumerate(bank_rows):
        color = colors[index % len(colors)]
        start = cursor
        cursor += float(row["value"]) / total * 100
        stops.append(f"{color} {start:.2f}% {cursor:.2f}%")
        bank = html.escape(str(row["bank"]))
        percent = float(row["percent"])
        legend_rows.append(
            f'<div class="bank-legend-row"><span class="bank-legend-dot" style="--legend-color:{color}"></span>'
            f'<span class="bank-legend-name" title="{bank}">{bank}</span>'
            f'<span class="bank-legend-value">{percent:g}%</span></div>'
        )

    gradient = ", ".join(stops)
    st.markdown(
        f'<div class="bank-donut-wrap"><div class="bank-donut" style="--donut-gradient: conic-gradient({gradient});">'
        f'<div class="bank-donut-center"><b>{_format_million(total)}</b><span>Tổng Tr</span></div></div>'
        f'<div class="bank-legend">{"".join(legend_rows)}</div></div>',
        unsafe_allow_html=True,
    )
