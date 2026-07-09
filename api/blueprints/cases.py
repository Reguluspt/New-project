from flask import Blueprint, request, jsonify, current_app, send_file
from api.middleware.auth import login_required
from src.sqlite_store import (
    init_db,
    connect,
    get_case,
    create_case,
    update_case,
    delete_case,
    distinct_case_values,
    MONTH_SORT_EXPR,
    SORTABLE_FIELDS,
    CASE_FIELDS
)
from src.case_excel_export import export_case_rows_to_excel
from src.form_options_store import load_custom_form_options
import math
import tempfile
from pathlib import Path

cases_bp = Blueprint("cases", __name__)

def query_cases(db_path, *, page=1, size=20, sort="id", order="desc", search="", status="", branch="", appraiser_name="", execution_month="", payment_status="", year="", valuation_branch="", exclude_status=""):
    init_db(db_path)
    
    conditions = []
    params = {}
    
    if search:
        conditions.append(
            """
            (
                INSTR(CASEFOLD(contract_number), :search) > 0
                OR INSTR(CASEFOLD(customer_info), :search) > 0
                OR INSTR(CASEFOLD(customer_address), :search) > 0
                OR INSTR(CASEFOLD(asset_description), :search) > 0
                OR INSTR(CASEFOLD(valuation_purpose), :search) > 0
                OR INSTR(CASEFOLD(source), :search) > 0
                OR INSTR(CASEFOLD(personal_note), :search) > 0
                OR INSTR(CASEFOLD(valuation_staff), :search) > 0
                OR INSTR(CASEFOLD(business_staff), :search) > 0
                OR INSTR(CASEFOLD(citizen_id), :search) > 0
                OR INSTR(CASEFOLD(customer_type), :search) > 0
                OR INSTR(CASEFOLD(case_status), :search) > 0
                OR INSTR(CASEFOLD(execution_month), :search) > 0
                OR INSTR(CASEFOLD(payment_status), :search) > 0
            )
            """
        )
        params["search"] = search.casefold()
        
    if status:
        conditions.append("case_status = :status")
        params["status"] = status
        
    if branch:
        conditions.append("source = :branch")
        params["branch"] = branch
        
    if valuation_branch:
        conditions.append("valuation_branch = :valuation_branch")
        params["valuation_branch"] = valuation_branch
        
    if appraiser_name:
        conditions.append("valuation_staff = :appraiser_name")
        params["appraiser_name"] = appraiser_name
        
    if execution_month:
        conditions.append("execution_month = :execution_month")
        params["execution_month"] = execution_month
        
    if payment_status:
        conditions.append("payment_status = :payment_status")
        params["payment_status"] = payment_status
        
    if exclude_status:
        conditions.append("COALESCE(case_status, '') <> :exclude_status")
        params["exclude_status"] = exclude_status
        
    if year:
        conditions.append("SUBSTR(execution_month, 4, 4) = :year")
        params["year"] = str(year)
        
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # Sort mapping
    sort_expr = "id"
    if sort == "id":
        sort_expr = "id"
    elif sort == "created_at":
        sort_expr = "created_at"
    elif sort == "execution_month":
        sort_expr = MONTH_SORT_EXPR
    elif sort == "valuation_fee":
        sort_expr = "COALESCE(valuation_fee_number, 0)"
    elif sort in SORTABLE_FIELDS:
        sort_expr = SORTABLE_FIELDS[sort]
    else:
        if sort in CASE_FIELDS:
            sort_expr = sort
            
    order_dir = "DESC" if order.lower() == "desc" else "ASC"
    
    # Count total matching records
    count_sql = f"SELECT COUNT(*) FROM cases {where}"
    
    # Fetch paginated data
    data_sql = f"SELECT * FROM cases {where} ORDER BY {sort_expr} {order_dir}, id {order_dir} LIMIT :limit OFFSET :offset"
    
    limit = size
    offset = (page - 1) * size
    params.update({"limit": limit, "offset": offset})
    
    with connect(db_path) as conn:
        total = conn.execute(count_sql, {k: v for k, v in params.items() if k not in ("limit", "offset")}).fetchone()[0]
        rows = conn.execute(data_sql, params).fetchall()
        
    items = []
    for row in rows:
        row_dict = dict(row)
        # Ensure STT index mapping or front-end keys map correctly
        items.append(row_dict)
        
    pages = math.ceil(total / size)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "size": size
    }

def get_distinct_valuation_staff(db_path):
    sql = "SELECT DISTINCT valuation_staff FROM cases WHERE valuation_staff IS NOT NULL AND TRIM(valuation_staff) <> '' ORDER BY valuation_staff"
    with connect(db_path) as conn:
        rows = conn.execute(sql).fetchall()
    return [str(row[0]) for row in rows]

@cases_bp.route("", methods=["GET"])
@login_required
def list_cases_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
    except ValueError:
        page = 1
        size = 20
        
    sort = request.args.get("sort", "id")
    order = request.args.get("order", "desc")
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    branch = request.args.get("branch", "")
    valuation_branch = request.args.get("valuation_branch", "")
    appraiser_name = request.args.get("appraiser_name", "")
    execution_month = request.args.get("execution_month", "")
    payment_status = request.args.get("payment_status", "")
    year = request.args.get("year", "")
    exclude_status = request.args.get("exclude_status", "")
    
    res = query_cases(
        db,
        page=page,
        size=size,
        sort=sort,
        order=order,
        search=search,
        status=status,
        branch=branch,
        appraiser_name=appraiser_name,
        execution_month=execution_month,
        payment_status=payment_status,
        year=year,
        valuation_branch=valuation_branch,
        exclude_status=exclude_status
    )
    return jsonify(res)

@cases_bp.route("/<int:case_id>", methods=["GET"])
@login_required
def get_case_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case_data = get_case(db, case_id)
    if not case_data:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
    return jsonify(case_data)

@cases_bp.route("", methods=["POST"])
@login_required
def create_case_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    try:
        new_id = create_case(db, data)
        return jsonify({"id": new_id, "success": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@cases_bp.route("/<int:case_id>", methods=["PUT"])
@login_required
def update_case_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    try:
        update_case(db, case_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@cases_bp.route("/<int:case_id>", methods=["DELETE"])
@login_required
def delete_case_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    try:
        delete_case(db, case_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@cases_bp.route("/<int:case_id>/status", methods=["PATCH"])
@login_required
def update_status_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "Trạng thái không hợp lệ"}), 400
    try:
        update_case(db, case_id, {"case_status": status})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@cases_bp.route("/<int:case_id>/payment", methods=["PATCH"])
@login_required
def update_payment_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    payment_status = data.get("payment_status")
    if not payment_status:
        return jsonify({"error": "Trạng thái thanh toán không hợp lệ"}), 400
    try:
        update_case(db, case_id, {"payment_status": payment_status})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@cases_bp.route("/import", methods=["POST"])
@login_required
def import_cases_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy file"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tên file rỗng"}), 400
        
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / file.filename
    file.save(temp_path)
    
    try:
        from src.sqlite_store import import_excel_database
        imported = import_excel_database(db, temp_path)
        return jsonify({"success": True, "imported": imported})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if temp_path.exists():
            temp_path.unlink()

@cases_bp.route("/export", methods=["GET"])
@login_required
def export_cases_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    branch = request.args.get("branch", "")
    valuation_branch = request.args.get("valuation_branch", "")
    appraiser_name = request.args.get("appraiser_name", "")
    execution_month = request.args.get("execution_month", "")
    payment_status = request.args.get("payment_status", "")
    year = request.args.get("year", "")
    
    # Query all matching records (large limit)
    res = query_cases(
        db,
        page=1,
        size=1000000,
        sort=request.args.get("sort", "id"),
        order=request.args.get("order", "desc"),
        search=search,
        status=status,
        branch=branch,
        appraiser_name=appraiser_name,
        execution_month=execution_month,
        payment_status=payment_status,
        year=year,
        valuation_branch=valuation_branch
    )
    
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / "cases_export.xlsx"
    
    try:
        export_case_rows_to_excel(res["items"], CASE_FIELDS, temp_path)
        return send_file(
            temp_path,
            as_attachment=True,
            download_name="cases_export.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@cases_bp.route("/filters", methods=["GET"])
@login_required
def filters_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    try:
        statuses = distinct_case_values(db, "case_status")
        branches = distinct_case_values(db, "source")
        appraisers = get_distinct_valuation_staff(db)
        execution_months = distinct_case_values(db, "execution_month")
        payment_statuses = distinct_case_values(db, "payment_status")
        
        from src.app_config import TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG
        import json
        excel_template_path = Path(DEFAULT_TEMPLATE_CONFIG["excel_template_path"])
        if Path(TEMPLATE_CONFIG_PATH).exists():
            try:
                with open(TEMPLATE_CONFIG_PATH, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    if config_data.get("excel_template_path"):
                        excel_template_path = Path(config_data["excel_template_path"])
            except Exception:
                pass
        
        from src.excel_writer import load_dropdown_options
        excel_options = load_dropdown_options(excel_template_path)
        custom_options = load_custom_form_options()

        def merge_options(*groups):
            seen = set()
            values = []
            for group in groups:
                for item in group or []:
                    text = str(item or "").strip()
                    if text and text not in seen:
                        seen.add(text)
                        values.append(text)
            return values

        valuation_purposes = merge_options(
            excel_options.get("valuation_purpose", []),
            custom_options.get("valuation_purpose", []),
        )
        asset_types = merge_options(
            excel_options.get("asset_type", []),
            custom_options.get("asset_type", []),
        )

        valuation_branches = merge_options(
            distinct_case_values(db, "valuation_branch"),
            custom_options.get("valuation_branch", []),
        )
        branches = merge_options(branches, custom_options.get("source", []))
        appraisers = merge_options(appraisers, custom_options.get("valuation_staff", []))
        offices = merge_options(custom_options.get("office", []))

        return jsonify({
            "statuses": statuses,
            "branches": branches,
            "valuation_branches": valuation_branches,
            "appraisers": appraisers,
            "execution_months": execution_months,
            "payment_statuses": payment_statuses,
            "valuation_purposes": valuation_purposes,
            "asset_types": asset_types,
            "offices": offices
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@cases_bp.route("/<int:case_id>/notes", methods=["GET"])
@login_required
def get_notes_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case_data = get_case(db, case_id)
    if not case_data:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    notes_text = case_data.get("personal_note") or ""
    notes = []
    if notes_text:
        # Split by newline
        for line in notes_text.split("\n"):
            if line.strip():
                notes.append({
                    "note": line.strip(),
                    "created_at": case_data.get("updated_at")
                })
    return jsonify(notes)

@cases_bp.route("/<int:case_id>/notes", methods=["POST"])
@login_required
def add_note_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case_data = get_case(db, case_id)
    if not case_data:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    data = request.get_json() or {}
    new_note = data.get("note", "").strip()
    if not new_note:
        return jsonify({"error": "Ghi chú trống"}), 400
        
    existing_notes = case_data.get("personal_note") or ""
    if existing_notes:
        updated_notes = f"{existing_notes}\n{new_note}"
    else:
        updated_notes = new_note
        
    try:
        update_case(db, case_id, {"personal_note": updated_notes})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@cases_bp.route("/<int:case_id>/remind-payment", methods=["POST"])
@login_required
def remind_payment_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case_data = get_case(db, case_id)
    if not case_data:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    data = request.get_json() or {}
    to_email = data.get("to_email", "").strip()
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()
    
    if not to_email:
        return jsonify({"error": "Email nhận không được trống"}), 400
    if not subject:
        return jsonify({"error": "Tiêu đề không được trống"}), 400
    if not body:
        return jsonify({"error": "Nội dung không được trống"}), 400
        
    try:
        import asyncio
        import datetime
        from src.oauth2_service import send_email_via_oauth2, load_oauth_config
        
        # Load outlook config sender email
        oauth_config = load_oauth_config()
        outlook_config = oauth_config.get("outlook", {})
        from_email = outlook_config.get("sender_email") or "truongpnt2@outlook.com.vn"
        
        # Convert plain text newlines to html line breaks
        html_body = f"<div style='font-family: Arial, sans-serif; line-height: 1.5; font-size: 14px;'>" + body.replace("\n", "<br>") + "</div>"
        
        asyncio.run(send_email_via_oauth2(
            provider="outlook",
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            html_body=html_body
        ))
        
        # Log to personal notes
        existing_notes = case_data.get("personal_note") or ""
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        reminder_note = f"[{timestamp}] Đã gửi email nhắc nợ đến {to_email}"
        updated_notes = f"{existing_notes}\n{reminder_note}" if existing_notes else reminder_note
        update_case(db, case_id, {"personal_note": updated_notes})
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
