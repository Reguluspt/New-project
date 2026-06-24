from flask import Blueprint, request, jsonify, current_app
from api.middleware.auth import login_required
import datetime
from src.sqlite_store import (
    init_db,
    search_cases,
    distinct_case_values,
    revenue_summary,
    monthly_revenue_breakdown
)
import re

dashboard_bp = Blueprint("dashboard", __name__)

def _bank_system_name(source: object) -> str:
    text = str(source or "").strip()
    if not text:
        return "Khác"
    return text.split(" - ", 1)[0].strip() or text

def get_status_counts(db_path, *, year="", source="", customer_type="", business_staff=""):
    """
    Direct database helper to get status counts based on filters.
    """
    from src.sqlite_store import _build_case_search, connect
    where, params = _build_case_search(
        "",
        source=source,
        customer_type=customer_type,
        business_staff=business_staff
    )
    
    conditions = []
    if where:
        conditions.append(where.removeprefix("WHERE ").strip())
        
    # Exclude canceled cases from totals if not requested
    # As per views/dashboard.py: COALESCE(case_status, '') <> CANCELED_CASE_STATUS
    from src.sqlite_store import CANCELED_CASE_STATUS, DEFAULT_CASE_STATUS
    conditions.append("COALESCE(case_status, '') <> :canceled_status")
    params["canceled_status"] = CANCELED_CASE_STATUS
    
    if year:
        conditions.append("SUBSTR(execution_month, 4, 4) = :year")
        params["year"] = str(year)
        
    final_where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    sql = f"""
        SELECT COALESCE(case_status, :default_status) as status, COUNT(*) as count
        FROM cases
        {final_where}
        GROUP BY status
    """
    params["default_status"] = DEFAULT_CASE_STATUS
    
    counts = {}
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            counts[row[0]] = row[1]
    return counts

def get_bank_revenue_breakdown(db_path, *, year="", status="", branch="", customer_type="", staff_name=""):
    from src.sqlite_store import _build_case_search, connect, CANCELED_CASE_STATUS
    where, params = _build_case_search(
        "",
        case_status=status,
        source=branch,
        customer_type=customer_type,
        business_staff=staff_name
    )
    conditions = []
    if where:
        conditions.append(where.removeprefix("WHERE ").strip())
    conditions.append("COALESCE(case_status, '') <> :canceled_status")
    params["canceled_status"] = CANCELED_CASE_STATUS
    
    if year:
        conditions.append("SUBSTR(execution_month, 4, 4) = :year")
        params["year"] = str(year)
        
    final_where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    sql = f"""
        SELECT source, COALESCE(valuation_fee_number, 0) as fee
        FROM cases
        {final_where}
    """
    
    totals = {}
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            src_name = _bank_system_name(row[0])
            totals[src_name] = totals.get(src_name, 0.0) + float(row[1] or 0)
            
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

def get_unpaid_cases(db_path, *, year="", status="", branch="", customer_type="", staff_name=""):
    from src.sqlite_store import _build_case_search, connect, CANCELED_CASE_STATUS
    from src.app_config import UNPAID_STATUS
    from src.contracts import short_contract_number
    
    where, params = _build_case_search(
        "",
        case_status=status,
        source=branch,
        customer_type=customer_type,
        business_staff=staff_name
    )
    
    conditions = []
    if where:
        conditions.append(where.removeprefix("WHERE ").strip())
    conditions.append("COALESCE(case_status, '') <> :canceled_status")
    params["canceled_status"] = CANCELED_CASE_STATUS
    
    conditions.append("payment_status = :unpaid_status")
    params["unpaid_status"] = UNPAID_STATUS
    
    if year:
        conditions.append("SUBSTR(execution_month, 4, 4) = :year")
        params["year"] = str(year)
        
    final_where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    sql = f"""
        SELECT id, contract_number, customer_info, source, COALESCE(valuation_fee_number, 0) as fee, customer_type, execution_month
        FROM cases
        {final_where}
        ORDER BY SUBSTR(execution_month, 7, 4) ASC, SUBSTR(execution_month, 4, 2) ASC
    """
    
    unpaid_list = []
    unpaid_total = 0.0
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            fee = float(row[4] or 0)
            unpaid_total += fee
            unpaid_list.append({
                "case_id": row[0],
                "contract_number": short_contract_number(row[1]),
                "customer_info": row[2] or "",
                "source": row[3] or "",
                "valuation_fee_number": fee,
                "customer_type": row[5] or "individual",
                "execution_month": row[6] or ""
            })
    return unpaid_list, unpaid_total

@dashboard_bp.route("/stats", methods=["GET"])
@login_required
def stats():
    db = current_app.config["SQLITE_DATABASE"]
    
    year = request.args.get("year", "").strip()
    branch = request.args.get("branch", "").strip()
    staff_name = request.args.get("staff_name", "").strip()
    status = request.args.get("status", "").strip()
    customer_type = request.args.get("customer_type", "").strip()
    selected_month_param = request.args.get("month", "").strip()
    
    # Handle "Tất cả" option which React frontend might send
    if branch == "Tất cả": branch = ""
    if staff_name == "Tất cả": staff_name = ""
    if status == "Tất cả": status = ""
    if customer_type == "Tất cả": customer_type = ""
    
    # Call monthly_revenue_breakdown to aggregate monthly data
    monthly_rows = monthly_revenue_breakdown(
        db,
        year=year,
        case_status=status,
        source=branch,
        customer_type=customer_type,
        business_staff=staff_name
    )
    
    # Determine the target month for revenue_summary
    month_options = [row["month"] for row in monthly_rows]
    current_month = datetime.datetime.now().strftime("%m/%Y")
    
    if selected_month_param and selected_month_param in month_options:
        target_month = selected_month_param
    elif current_month in month_options:
        target_month = current_month
    elif month_options:
        target_month = month_options[-1]
    else:
        target_month = f"01/{year}" if year else current_month
        
    # Get revenue summary for the selected target month
    summary = revenue_summary(
        db,
        target_month=target_month,
        case_status=status,
        source=branch,
        customer_type=customer_type,
        business_staff=staff_name
    )
    
    # Calculate year totals
    year_projected = sum(row["projected_revenue"] for row in monthly_rows)
    year_paid = sum(row["paid_revenue"] for row in monthly_rows)
    year_unpaid = sum(row["unpaid_revenue"] for row in monthly_rows)
    
    # Get status counts
    counts = get_status_counts(db, year=year, source=branch, customer_type=customer_type, business_staff=staff_name)
    total_cases = sum(counts.values())
    
    # Format monthly revenue breakdown
    monthly_revenue = []
    for r in monthly_rows:
        monthly_revenue.append({
            "month": r["month"],
            "projected": r["projected_revenue"],
            "paid": r["paid_revenue"],
            "unpaid": r["unpaid_revenue"],
            "case_count": r["case_count"]
        })
        
    # Get bank revenue breakdown
    bank_revenue = get_bank_revenue_breakdown(
        db,
        year=year,
        status=status,
        branch=branch,
        customer_type=customer_type,
        staff_name=staff_name
    )
    
    # Get unpaid cases for the selected year
    unpaid_cases, unpaid_total = get_unpaid_cases(
        db,
        year=year,
        status=status,
        branch=branch,
        customer_type=customer_type,
        staff_name=staff_name
    )
    
    return jsonify({
      "year_projected": year_projected,
      "year_paid": year_paid,
      "year_unpaid": year_unpaid,
      "month_projected": summary.get("projected_current_month", 0),
      "selected_month": target_month,
      "total_cases": total_cases,
      "status_counts": counts,
      "monthly_revenue": monthly_revenue,
      "bank_revenue": bank_revenue,
      "unpaid_cases": unpaid_cases,
      "unpaid_total": unpaid_total,
      "unpaid_count": len(unpaid_cases)
    })

@dashboard_bp.route("/recent-cases", methods=["GET"])
@login_required
def recent_cases_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    
    limit_val = request.args.get("limit", "20")
    try:
        limit = int(limit_val)
    except ValueError:
        limit = 20
        
    year = request.args.get("year", "").strip()
    branch = request.args.get("branch", "").strip()
    staff_name = request.args.get("staff_name", "").strip()
    
    if branch == "Tất cả": branch = ""
    if staff_name == "Tất cả": staff_name = ""
    
    # search_cases sorts by created_at desc by default, but we can query with a larger limit to filter by year
    cases = search_cases(
        db,
        source=branch,
        business_staff=staff_name,
        sort_field="id",
        sort_direction="desc",
        limit=5000
    )
    
    # Filter by year in memory if needed
    if year:
        cases = [c for c in cases if c.get("execution_month") and str(c.get("execution_month")).endswith(f"/{year}")]
        
    cases = cases[:limit]
    
    response_data = []
    for c in cases:
        response_data.append({
            "case_id": c.get("id"),
            "contract_number": c.get("contract_number"),
            "customer_info": c.get("customer_info"),
            "status": c.get("case_status"),
            "execution_month": c.get("execution_month"),
            "valuation_fee": c.get("valuation_fee_number"),
            "payment_status": c.get("payment_status")
        })
        
    return jsonify(response_data)

@dashboard_bp.route("/filters", methods=["GET"])
@login_required
def filters():
    db = current_app.config["SQLITE_DATABASE"]
    
    branches = distinct_case_values(db, "source")
    staff_names = distinct_case_values(db, "business_staff")
    statuses = distinct_case_values(db, "case_status")
    execution_months = distinct_case_values(db, "execution_month")
    customer_types = distinct_case_values(db, "customer_type")
    
    years = sorted(list({m.split("/")[1] for m in execution_months if "/" in m}), reverse=True)
    
    return jsonify({
        "years": years,
        "branches": branches,
        "staff_names": staff_names,
        "statuses": statuses,
        "customer_types": customer_types
    })

