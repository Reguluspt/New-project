from flask import Blueprint, request, jsonify, current_app, send_file
from api.middleware.auth import login_required
from pathlib import Path
import asyncio
import aiosqlite
import zipfile
import io
import math
from datetime import datetime

from src.database_manager import resolve_records_db_path, delete_sobo_record, create_sobo_record, ensure_sobo_schema
from src.sqlite_store import get_case

sobo_bp = Blueprint("sobo", __name__)

async def query_sobo_records(db_path, search, status, page, size, sort, order):
    await ensure_sobo_schema(db_path)
    conditions = ["COALESCE(follow_replies, 1) = 1"]
    params = []
    
    if search:
        like_pat = f"%{search}%"
        conditions.append("""(
            dia_chi LIKE ? 
            OR so_thua LIKE ? 
            OR so_to LIKE ? 
            OR equipment_name LIKE ? 
            OR source LIKE ? 
            OR outbound_subject LIKE ? 
            OR email_recipient LIKE ?
            OR note LIKE ?
        )""")
        params.extend([like_pat] * 8)
        
    if status:
        conditions.append("status = ?")
        params.append(status.upper())
        
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    allowed_sorts = {
        "id": "id",
        "created_at": "created_at",
        "asset_type": "asset_type",
        "email_recipient": "email_recipient",
        "status": "status",
        "outbound_sent_at": "outbound_sent_at"
    }
    sort_field = allowed_sorts.get(sort, "id")
    order_dir = "DESC" if order.lower() == "desc" else "ASC"
    
    count_query = f"SELECT COUNT(*) FROM sobo_records {where_clause}"
    select_query = f"SELECT * FROM sobo_records {where_clause} ORDER BY {sort_field} {order_dir} LIMIT ? OFFSET ?"
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(count_query, params) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0
            
        offset = (page - 1) * size
        select_params = params + [size, offset]
        async with db.execute(select_query, select_params) as cursor:
            rows = await cursor.fetchall()
            items = [dict(row) for row in rows]
            
    pages = math.ceil(total / size) if size > 0 else 0
    return items, total, pages

async def get_sobo_record_by_id(db_path, record_id):
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sobo_records WHERE id = ?", (record_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_sobo_record_in_db(db_path, record_id, update_data):
    allowed_fields = {
        "asset_type", "asset_sub_type", "source", "so_thua", "so_to", "dia_chi",
        "link", "email_recipient", "status", "note", "equipment_name", "attachment_paths",
        "response_content", "follow_replies"
    }
    fields_to_set = []
    params = []
    for k, v in update_data.items():
        if k in allowed_fields:
            fields_to_set.append(f"{k} = ?")
            params.append(v)
    if not fields_to_set:
        return False
        
    params.append(record_id)
    query = f"UPDATE sobo_records SET {', '.join(fields_to_set)} WHERE id = ?"
    async with aiosqlite.connect(db_path) as db:
        await db.execute(query, params)
        await db.commit()
    return True

def collect_existing_paths(value: str) -> list[Path]:
    paths = []
    for item in str(value or "").splitlines():
        raw_path = item.strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        if path.exists() and path.is_file():
            paths.append(path)
    return paths

@sobo_bp.route("/sobo", methods=["GET"])
@login_required
def get_sobo_list():
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    sort = request.args.get("sort", "id").strip()
    order = request.args.get("order", "desc").strip()
    
    try:
        items, total, pages = asyncio.run(query_sobo_records(db_path, search, status, page, size, sort, order))
        return jsonify({
            "items": items,
            "total": total,
            "page": page,
            "pages": pages
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@sobo_bp.route("/sobo/stats", methods=["GET"])
@login_required
def get_sobo_stats():
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        from src.database_manager import get_all_sobo_records
        records = asyncio.run(get_all_sobo_records(db_path))
        
        pending_count = 0
        responded_count = 0
        total_reply_seconds = 0.0
        responded_with_time_count = 0
        has_overdue = False
        
        now = datetime.now()
        
        for r in records:
            follow_replies = r.get("follow_replies")
            if follow_replies is not None and int(follow_replies) == 0:
                continue

            status = r.get("status") or "PENDING"
            sent_time_str = r.get("outbound_sent_at") or r.get("created_at")
            resp_time_str = r.get("responded_at")
            
            sent_time = None
            if sent_time_str:
                for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        sent_time = datetime.strptime(sent_time_str, fmt)
                        break
                    except ValueError:
                        continue
                    
            resp_time = None
            if resp_time_str:
                for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        resp_time = datetime.strptime(resp_time_str, fmt)
                        break
                    except ValueError:
                        continue
                        
            if status == "PENDING":
                pending_count += 1
                if sent_time:
                    elapsed_secs = (now - sent_time).total_seconds()
                    if elapsed_secs >= 86400:
                        has_overdue = True
            elif status == "RESPONDED":
                responded_count += 1
                if sent_time and resp_time:
                    duration_secs = (resp_time - sent_time).total_seconds()
                    total_reply_seconds += duration_secs
                    responded_with_time_count += 1
                    
        avg_duration_secs = total_reply_seconds / responded_with_time_count if responded_with_time_count > 0 else 0
        
        return jsonify({
            "pending_count": pending_count,
            "responded_count": responded_count,
            "avg_duration_secs": avg_duration_secs,
            "has_overdue": has_overdue
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>", methods=["GET"])
@login_required
def get_sobo_detail(record_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        record = asyncio.run(get_sobo_record_by_id(db_path, record_id))
        if not record:
            return jsonify({"error": "Không tìm thấy hồ sơ sơ bộ"}), 404
        return jsonify(record)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>", methods=["PUT"])
@login_required
def update_sobo_record_endpoint(record_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    data = request.get_json() or {}
    try:
        updated = asyncio.run(update_sobo_record_in_db(db_path, record_id, data))
        if not updated:
            return jsonify({"error": "Không có trường hợp lệ nào để cập nhật"}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>/unfollow", methods=["POST"])
@login_required
def unfollow_sobo_record_endpoint(record_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        record = asyncio.run(get_sobo_record_by_id(db_path, record_id))
        if not record:
            return jsonify({"error": "Không tìm thấy hồ sơ sơ bộ"}), 404
        asyncio.run(update_sobo_record_in_db(db_path, record_id, {"follow_replies": 0}))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>", methods=["DELETE"])
@login_required
def delete_sobo_record_endpoint(record_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        asyncio.run(delete_sobo_record(db_path, record_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>/files", methods=["GET"])
@login_required
def get_sobo_files_list(record_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        record = asyncio.run(get_sobo_record_by_id(db_path, record_id))
        if not record:
            return jsonify({"error": "Không tìm thấy hồ sơ sơ bộ"}), 404
            
        paths = collect_existing_paths(record.get("attachment_paths") or "")
        files_info = []
        for p in paths:
            files_info.append({
                "filename": p.name,
                "size": p.stat().st_size,
                "url": f"/api/sobo/{record_id}/files/{p.name}"
            })
        return jsonify(files_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>/files/<filename>", methods=["GET"])
@login_required
def download_sobo_single_file(record_id, filename):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        record = asyncio.run(get_sobo_record_by_id(db_path, record_id))
        if not record:
            return jsonify({"error": "Không tìm thấy hồ sơ sơ bộ"}), 404
            
        paths = collect_existing_paths(record.get("attachment_paths") or "")
        target_path = None
        for p in paths:
            if p.name == filename:
                target_path = p
                break
                
        if not target_path:
            return jsonify({"error": f"Không tìm thấy file: {filename}"}), 404
            
        return send_file(target_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/<int:record_id>/files/download-all", methods=["GET"])
@login_required
def download_sobo_all_files(record_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        record = asyncio.run(get_sobo_record_by_id(db_path, record_id))
        if not record:
            return jsonify({"error": "Không tìm thấy hồ sơ sơ bộ"}), 404
            
        paths = collect_existing_paths(record.get("attachment_paths") or "")
        if not paths:
            return jsonify({"error": "Không có tệp đính kèm nào khả dụng"}), 404
            
        if len(paths) == 1:
            return send_file(paths[0], as_attachment=True)
            
        buffer = io.BytesIO()
        used_names = set()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for index, p in enumerate(paths, 1):
                arcname = p.name
                if arcname in used_names:
                    arcname = f"{p.stem}_{index}{p.suffix}"
                used_names.add(arcname)
                archive.write(p, arcname=arcname)
                
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"sobo_{record_id}_GCN.zip",
            mimetype="application/zip"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/from-case/<int:case_id>", methods=["POST"])
@login_required
def create_sobo_from_case(case_id):
    sqlite_db = current_app.config["SQLITE_DATABASE"]
    records_db = resolve_records_db_path(current_app.config["RECORDS_DB"])
    
    try:
        case = get_case(sqlite_db, case_id)
        if not case:
            return jsonify({"error": "Không tìm thấy hồ sơ gốc"}), 404
            
        payload = {
            "asset_type": case.get("asset_type") or "real_estate",
            "so_thua": case.get("so_thua_dat") or "",
            "so_to": case.get("so_to_ban_do") or "",
            "dia_chi": case.get("dia_chi_thua_dat") or "",
            "source": case.get("source") or "",
            "note": case.get("asset_description") or "",
            "email_recipient": case.get("valuation_staff") or "",
            "attachment_paths": case.get("original_file_path") or "",
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "outbound_sent_at": datetime.now().isoformat()
        }
        
        new_id = asyncio.run(create_sobo_record(records_db, payload))
        return jsonify({"id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/sync-telegram", methods=["POST"])
@login_required
def sync_telegram_endpoint():
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        from src.database_manager import sync_telegram_records_to_sobo
        from src.mail_listener import sync_sobo_emails_from_mailbox
        synced_db = asyncio.run(sync_telegram_records_to_sobo(db_path))
        synced_mail = asyncio.run(sync_sobo_emails_from_mailbox(db_path))
        return jsonify({
            "synced_db": synced_db,
            "synced_mail": synced_mail,
            "total": synced_db + synced_mail
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sobo_bp.route("/sobo/check-mail", methods=["POST"])
@login_required
def check_mail_endpoint():
    try:
        from src.mail_listener import poll_unseen_once, load_mail_listener_settings
        settings = load_mail_listener_settings()
        processed_count = asyncio.run(poll_unseen_once(settings))
        return jsonify({
            "processed_count": processed_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
