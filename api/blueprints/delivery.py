from flask import Blueprint, request, jsonify, current_app
from api.middleware.auth import login_required
import asyncio
import aiosqlite
from src.database_manager import resolve_records_db_path

delivery_bp = Blueprint("delivery", __name__)

async def query_delivery_contacts(db_path, search):
    query = "SELECT * FROM delivery_contacts"
    params = []
    if search:
        query += " WHERE short_name LIKE ? OR full_details LIKE ?"
        like_pat = f"%{search}%"
        params.extend([like_pat, like_pat])
    query += " ORDER BY short_name ASC"
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def add_delivery_contact_db(db_path, short_name, full_details):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "INSERT INTO delivery_contacts (short_name, full_details) VALUES (?, ?)",
            (short_name, full_details)
        )
        await db.commit()
        return cursor.lastrowid

async def update_delivery_contact_db(db_path, contact_id, short_name, full_details):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE delivery_contacts SET short_name = ?, full_details = ? WHERE id = ?",
            (short_name, full_details, contact_id)
        )
        await db.commit()

async def delete_delivery_contact_db(db_path, contact_id):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM delivery_contacts WHERE id = ?", (contact_id,))
        await db.commit()

@delivery_bp.route("/delivery/contacts", methods=["GET"])
@login_required
def get_delivery_contacts_endpoint():
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    search = request.args.get("search", "").strip()
    try:
        contacts = asyncio.run(query_delivery_contacts(db_path, search))
        return jsonify(contacts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@delivery_bp.route("/delivery/contacts", methods=["POST"])
@login_required
def create_delivery_contact_endpoint():
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    data = request.get_json() or {}
    
    short_name = str(data.get("short_name") or "").strip()
    full_details = str(data.get("full_details") or "").strip()
    
    if not short_name or not full_details:
        return jsonify({"error": "Tên gợi nhớ và thông tin chi tiết là bắt buộc"}), 400
        
    try:
        contact_id = asyncio.run(add_delivery_contact_db(db_path, short_name, full_details))
        return jsonify({"id": contact_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@delivery_bp.route("/delivery/contacts/<int:contact_id>", methods=["PUT"])
@login_required
def update_delivery_contact_endpoint(contact_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    data = request.get_json() or {}
    
    short_name = str(data.get("short_name") or "").strip()
    full_details = str(data.get("full_details") or "").strip()
    
    if not short_name or not full_details:
        return jsonify({"error": "Tên gợi nhớ và thông tin chi tiết là bắt buộc"}), 400
        
    try:
        asyncio.run(update_delivery_contact_db(db_path, contact_id, short_name, full_details))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@delivery_bp.route("/delivery/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def delete_delivery_contact_endpoint(contact_id):
    db_path = resolve_records_db_path(current_app.config["RECORDS_DB"])
    try:
        asyncio.run(delete_delivery_contact_db(db_path, contact_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
