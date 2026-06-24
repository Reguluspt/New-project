from flask import Blueprint, request, jsonify, current_app
from api.middleware.auth import login_required
from pathlib import Path
import os
import sqlite3
import uuid

from src.sqlite_store import (
    get_all_organizations,
    add_organization,
    update_organization,
    delete_organization
)

organizations_bp = Blueprint("organizations", __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def merge_organizations(db_path, source_id, target_id):
    # Retrieve source and target orgs
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        source = conn.execute("SELECT * FROM organizations WHERE id = ?", (source_id,)).fetchone()
        target = conn.execute("SELECT * FROM organizations WHERE id = ?", (target_id,)).fetchone()
        if not source or not target:
            raise ValueError("Không tìm thấy tổ chức nguồn hoặc đích")
            
        source = dict(source)
        target = dict(target)
        
        # Merge empty fields from source to target
        updates = {}
        for field in ["tax_code", "name", "abbreviation", "address", "representative", "position"]:
            if not str(target.get(field) or "").strip() and str(source.get(field) or "").strip():
                updates[field] = source[field]
                
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            params = list(updates.values()) + [target_id]
            conn.execute(f"UPDATE organizations SET {set_clause} WHERE id = ?", params)
            
        # Optional: update cases referencing the source organization's tax code or name
        source_tax = str(source.get("tax_code") or "").strip()
        target_tax = str(target.get("tax_code") or "").strip()
        source_name = str(source.get("name") or "").strip()
        target_name = str(target.get("name") or "").strip()
        
        if source_tax and target_tax:
            conn.execute("UPDATE cases SET tax_code = ? WHERE tax_code = ?", (target_tax, source_tax))
        if source_name and target_name:
            conn.execute("UPDATE cases SET customer_info = ? WHERE customer_info = ?", (target_name, source_name))
            
        # Delete source organization
        conn.execute("DELETE FROM organizations WHERE id = ?", (source_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@organizations_bp.route("/organizations", methods=["GET"])
@login_required
def get_organizations_list():
    db_path = current_app.config["SQLITE_DATABASE"]
    search = request.args.get("search", "").strip().lower()
    
    try:
        orgs = get_all_organizations(db_path)
        if search:
            orgs = [
                org for org in orgs
                if search in str(org.get("name") or "").lower()
                or search in str(org.get("tax_code") or "").lower()
                or search in str(org.get("abbreviation") or "").lower()
                or search in str(org.get("representative") or "").lower()
            ]
        return jsonify(orgs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@organizations_bp.route("/organizations", methods=["POST"])
@login_required
def create_organization_endpoint():
    db_path = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Tên công ty là bắt buộc"}), 400
        
    try:
        org_id = add_organization(db_path, data)
        return jsonify({"id": org_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@organizations_bp.route("/organizations/<int:org_id>", methods=["PUT"])
@login_required
def update_organization_endpoint(org_id):
    db_path = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Tên công ty là bắt buộc"}), 400
        
    try:
        update_organization(db_path, org_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@organizations_bp.route("/organizations/<int:org_id>", methods=["DELETE"])
@login_required
def delete_organization_endpoint(org_id):
    db_path = current_app.config["SQLITE_DATABASE"]
    try:
        delete_organization(db_path, org_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@organizations_bp.route("/organizations/merge", methods=["POST"])
@login_required
def merge_organizations_endpoint():
    db_path = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    
    source_id = data.get("source_id")
    target_id = data.get("target_id")
    if not source_id or not target_id:
        return jsonify({"error": "source_id và target_id là bắt buộc"}), 400
        
    try:
        merge_organizations(db_path, int(source_id), int(target_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@organizations_bp.route("/organizations/ai-extract", methods=["POST"])
@login_required
def ai_extract_organization_endpoint():
    if "files" not in request.files and "file" not in request.files:
        return jsonify({"error": "Không có file upload"}), 400
        
    files = request.files.getlist("files") or request.files.getlist("file")
    
    from src.app_config import load_ai_config, AI_CONFIG_PATH
    ai_config = load_ai_config(AI_CONFIG_PATH)
    prov_settings = ai_config.get("providers", {}).get("Gemini", {})
    
    api_key = prov_settings.get("api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Chưa cấu hình Gemini API Key"}), 400
        
    model = prov_settings.get("model") or "gemini-2.5-flash"
    
    upload_dir = PROJECT_ROOT / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    from src.gemini_extractor import extract_organization_from_contract_with_gemini
    
    for f in files:
        if not f.filename:
            continue
        temp_path = upload_dir / f"{uuid.uuid4().hex}_{f.filename}"
        f.save(temp_path)
        
        try:
            extraction = extract_organization_from_contract_with_gemini(temp_path, api_key=api_key, model=model)
            results.append({
                "tax_code": extraction.tax_code or "",
                "name": extraction.name or "",
                "abbreviation": "",
                "address": extraction.address or "",
                "representative": extraction.representative or "",
                "position": extraction.position or ""
            })
        except Exception as e:
            return jsonify({"error": f"Lỗi trích xuất tệp {f.filename}: {str(e)}"}), 500
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
                    
    return jsonify(results)
