from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.app_config import UNPAID_STATUS
from src.database_store import format_money
from src.sqlite_store import (
    CANCELED_CASE_STATUS,
    DEFAULT_CASE_STATUS,
    count_cases,
    display_cases,
    distinct_case_values,
    revenue_summary,
    search_cases,
)

ALL_OPTION = "Tất cả"
SORT_FIELD_OPTIONS = {
    "Ngày tạo": "created_at",
    "Trạng thái hồ sơ": "case_status",
    "Tháng thực hiện": "execution_month",
    "Phí thẩm định": "valuation_fee_number",
    "Khách hàng": "customer_info",
    "Số hợp đồng": "contract_number",
    "Trạng thái thanh toán": "payment_status",
    "Nguồn/ngân hàng": "source",
}
CUSTOMER_TYPE_LABELS = {
    "individual": "Cá nhân",
    "organization": "Tổ chức",
}


def filter_value(selected: str) -> str:
    return "" if selected == ALL_OPTION else selected


def load_filter_options(db_path: Path) -> dict[str, list[str]]:
    return {
        "case_status": [ALL_OPTION] + distinct_case_values(db_path, "case_status"),
        "execution_month": [ALL_OPTION] + distinct_case_values(db_path, "execution_month"),
        "payment_status": [ALL_OPTION] + distinct_case_values(db_path, "payment_status"),
        "source": [ALL_OPTION] + distinct_case_values(db_path, "source"),
        "customer_type": [ALL_OPTION] + distinct_case_values(db_path, "customer_type"),
        "business_staff": [ALL_OPTION] + distinct_case_values(db_path, "business_staff"),
    }


def build_filters(
    *,
    selected_execution_month: str,
    selected_payment_status: str,
    selected_case_status: str,
    selected_source: str,
    selected_customer_type: str,
    selected_business_staff: str,
) -> dict[str, str]:
    return {
        "execution_month": filter_value(selected_execution_month),
        "payment_status": filter_value(selected_payment_status),
        "case_status": filter_value(selected_case_status),
        "source": filter_value(selected_source),
        "customer_type": filter_value(selected_customer_type),
        "business_staff": filter_value(selected_business_staff),
    }


def count_filtered_cases(db_path: Path, query: str, filters: dict[str, str], note_query: str = "") -> int:
    return count_cases(
        db_path,
        query,
        note_query=note_query,
        case_status=filters["case_status"],
        execution_month=filters["execution_month"],
        payment_status=filters["payment_status"],
        source=filters["source"],
        customer_type=filters["customer_type"],
        business_staff=filters["business_staff"],
    )


def get_revenue_context(db_path: Path, query: str, filters: dict[str, str], note_query: str = "") -> dict[str, Any]:
    target_month = filters["execution_month"] or datetime.now().strftime("%m/%Y")
    summary = revenue_summary(
        db_path,
        target_month=target_month,
        query=query,
        note_query=note_query,
        case_status=filters["case_status"],
        payment_status=filters["payment_status"],
        source=filters["source"],
        customer_type=filters["customer_type"],
        business_staff=filters["business_staff"],
    )
    return {"target_month": target_month, "summary": summary}


def build_chart_rows(summary: dict[str, Any], total_matches: int) -> list[dict[str, Any]]:
    chart_rows = list(summary["previous_months"])
    chart_rows.append(
        {
            "Tháng": summary["target_month"],
            "Số hồ sơ": int(summary.get("case_count_current_month", total_matches)),
            "Doanh thu dự kiến": summary["projected_current_month"],
            "Đã thanh toán": summary["paid_current_month"],
            "Chưa thanh toán": summary["unpaid_current_month"],
        }
    )
    return sorted(chart_rows, key=lambda item: datetime.strptime(item["Tháng"], "%m/%Y"))


def build_chart_data(chart_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chart_data: list[dict[str, Any]] = []
    for row in chart_rows:
        chart_data.extend(
            [
                {"Tháng": row["Tháng"], "Chỉ tiêu": "Doanh thu dự kiến", "Giá trị": row["Doanh thu dự kiến"]},
                {"Tháng": row["Tháng"], "Chỉ tiêu": "Đã thanh toán", "Giá trị": row["Đã thanh toán"]},
                {"Tháng": row["Tháng"], "Chỉ tiêu": "Chưa thanh toán", "Giá trị": row["Chưa thanh toán"]},
            ]
        )
    return chart_data


def format_previous_month_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "Doanh thu dự kiến": format_money(row["Doanh thu dự kiến"]),
            "Đã thanh toán": format_money(row["Đã thanh toán"]),
            "Chưa thanh toán": format_money(row["Chưa thanh toán"]),
        }
        for row in summary["previous_months"]
    ]


def get_unpaid_report(db_path: Path, query: str, filters: dict[str, str], note_query: str = "") -> dict[str, Any]:
    unpaid_count = count_cases(
        db_path,
        query,
        note_query=note_query,
        case_status=filters["case_status"],
        execution_month=filters["execution_month"],
        payment_status=UNPAID_STATUS,
        source=filters["source"],
        customer_type=filters["customer_type"],
        business_staff=filters["business_staff"],
    )
    unpaid_rows = search_cases(
        db_path,
        query,
        note_query=note_query,
        case_status=filters["case_status"],
        execution_month=filters["execution_month"],
        payment_status=UNPAID_STATUS,
        source=filters["source"],
        customer_type=filters["customer_type"],
        business_staff=filters["business_staff"],
        sort_field="execution_month",
        sort_direction="asc",
        limit=max(unpaid_count, 1),
        offset=0,
    )
    unpaid_rows = [row for row in unpaid_rows if (row.get("case_status") or DEFAULT_CASE_STATUS) != CANCELED_CASE_STATUS]
    unpaid_total = sum(float(row.get("valuation_fee_number") or 0) for row in unpaid_rows)
    report_rows = [
        {
            "_id": row.get("id"),
            "Tháng thực hiện": row.get("execution_month") or "",
            "Số hợp đồng": row.get("contract_number") or "",
            "Khách hàng": row.get("customer_info") or "",
            "Loại khách hàng": CUSTOMER_TYPE_LABELS.get(row.get("customer_type"), row.get("customer_type") or ""),
            "Nguồn/ngân hàng": row.get("source") or "",
            "Chuyên viên kinh doanh": row.get("business_staff") or "",
            "Phí thẩm định": format_money(row.get("valuation_fee_number")),
            "Trạng thái thanh toán": row.get("payment_status") or "",
            "Địa chỉ khách hàng": row.get("customer_address") or "",
            "Ghi chú cá nhân": row.get("personal_note") or "",
        }
        for row in unpaid_rows
    ]
    return {"count": len(unpaid_rows), "total": unpaid_total, "rows": report_rows}


def search_page(
    db_path: Path,
    query: str,
    filters: dict[str, str],
    *,
    note_query: str = "",
    sort_field: str,
    sort_direction: str,
    page_size: int,
    page_number: int,
) -> list[dict[str, Any]]:
    return search_cases(
        db_path,
        query,
        note_query=note_query,
        case_status=filters["case_status"],
        execution_month=filters["execution_month"],
        payment_status=filters["payment_status"],
        source=filters["source"],
        customer_type=filters["customer_type"],
        business_staff=filters["business_staff"],
        sort_field=sort_field,
        sort_direction=sort_direction,
        limit=page_size,
        offset=(int(page_number) - 1) * page_size,
    )


def build_visible_display_rows(rows: list[dict[str, Any]], visible_columns: list[str]) -> list[dict[str, Any]]:
    rendered_rows = display_cases(rows)
    return [{column: row.get(column, "") for column in visible_columns} for row in rendered_rows]


def display_columns(rows: list[dict[str, Any]]) -> list[str]:
    rendered_rows = display_cases(rows)
    return list(rendered_rows[0].keys()) if rendered_rows else []


def export_rows_for_filters(
    db_path: Path,
    query: str,
    filters: dict[str, str],
    *,
    note_query: str = "",
    visible_columns: list[str],
    sort_field: str,
    sort_direction: str,
    export_count: int,
) -> list[dict[str, Any]]:
    export_rows = search_cases(
        db_path,
        query,
        note_query=note_query,
        case_status=filters["case_status"],
        execution_month=filters["execution_month"],
        payment_status=filters["payment_status"],
        source=filters["source"],
        customer_type=filters["customer_type"],
        business_staff=filters["business_staff"],
        sort_field=sort_field,
        sort_direction=sort_direction,
        limit=max(export_count, 1),
        offset=0,
    )
    return build_visible_display_rows(export_rows, visible_columns)


def export_scope_label(query: str, filters: dict[str, str]) -> str:
    parts = [query.strip() or "Tất cả hồ sơ"]
    if filters["execution_month"]:
        parts.append(filters["execution_month"])
    if filters["payment_status"]:
        parts.append(filters["payment_status"])
    if filters["case_status"]:
        parts.append(filters["case_status"])
    if filters["source"]:
        parts.append(filters["source"])
    if filters["customer_type"]:
        parts.append(CUSTOMER_TYPE_LABELS.get(filters["customer_type"], filters["customer_type"]))
    if filters["business_staff"]:
        parts.append(filters["business_staff"])
    return " | ".join(parts)
