from flask import Blueprint, request, jsonify, current_app, send_file
from api.middleware.auth import login_required
from pathlib import Path
from datetime import datetime
import os

from src.app_config import TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG, TEMPLATE_HISTORY_PATH, TEMPLATE_VERSIONS_DIR
from src.template_manager import (
    load_template_config,
    list_docx_templates,
    extract_placeholders_from_docx,
    read_docx_text,
    create_template_snapshot,
    append_template_history,
    read_template_history
)

templates_bp = Blueprint("templates", __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def find_template_path(name):
    config = load_template_config(TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG)
    ind_dir = Path(config["individual_template_dir"])
    org_dir = Path(config["organization_template_dir"])
    
    for d in [ind_dir, org_dir]:
        if d.exists() and d.is_dir():
            p = d / name
            if p.exists() and p.is_file():
                return p
    return None

@templates_bp.route("/templates", methods=["GET"])
@login_required
def get_templates_list():
    config = load_template_config(TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG)
    
    # Safely resolve directories, fallback to project root relative path if needed
    ind_dir = Path(config["individual_template_dir"])
    if not ind_dir.is_absolute():
        ind_dir = PROJECT_ROOT / ind_dir
        
    org_dir = Path(config["organization_template_dir"])
    if not org_dir.is_absolute():
        org_dir = PROJECT_ROOT / org_dir
        
    templates = []
    
    for d in [ind_dir, org_dir]:
        if d.exists() and d.is_dir():
            for f in d.glob("*.docx"):
                stat = f.stat()
                templates.append({
                    "name": f.name,
                    "path": str(f),
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
                
    return jsonify(templates)

@templates_bp.route("/templates/<name>", methods=["GET"])
@login_required
def get_template_detail(name):
    path = find_template_path(name)
    if not path:
        return jsonify({"error": "Không tìm thấy mẫu thiết kế"}), 404
        
    try:
        placeholders = extract_placeholders_from_docx(path)
        text = read_docx_text(path)
        content_preview = text[:500] + "..." if len(text) > 500 else text
        
        stat = path.stat()
        
        return jsonify({
            "name": name,
            "path": str(path),
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_preview": content_preview,
            "placeholders": placeholders
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@templates_bp.route("/templates/<name>", methods=["PUT"])
@login_required
def upload_template_version(name):
    if "file" not in request.files:
        return jsonify({"error": "Không có tệp tải lên"}), 400
        
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tên tệp không hợp lệ"}), 400
        
    path = find_template_path(name)
    if not path:
        return jsonify({"error": "Không tìm thấy mẫu thiết kế để cập nhật"}), 404
        
    try:
        # 1. Create a version snapshot before overwrite
        versions_root = Path(TEMPLATE_VERSIONS_DIR)
        if not versions_root.is_absolute():
            versions_root = PROJECT_ROOT / versions_root
        versions_root.mkdir(parents=True, exist_ok=True)
        
        create_template_snapshot(path, versions_root, reason="before_upload")
        
        # 2. Overwrite the template docx file
        file.save(path)
        
        # 3. Append to history log
        history_path = Path(TEMPLATE_HISTORY_PATH)
        if not history_path.is_absolute():
            history_path = PROJECT_ROOT / history_path
            
        editor_name = request.form.get("editor_name", "Flask Admin").strip()
        description = request.form.get("description", "Cập nhật phiên bản qua web client").strip()
        
        append_template_history(
            history_path,
            template_path=path,
            editor_name=editor_name,
            action="upload_version",
            details={"description": description, "filename": file.filename}
        )
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@templates_bp.route("/templates/<name>/history", methods=["GET"])
@login_required
def get_template_history(name):
    path = find_template_path(name)
    if not path:
        return jsonify({"error": "Không tìm thấy mẫu thiết kế"}), 404
        
    history_path = Path(TEMPLATE_HISTORY_PATH)
    if not history_path.is_absolute():
        history_path = PROJECT_ROOT / history_path
        
    try:
        raw_history = read_template_history(history_path, template_path=path)
        formatted_history = []
        for idx, item in enumerate(raw_history, 1):
            formatted_history.append({
                "version": f"v{idx}",
                "action": item.get("action") or "upload_version",
                "modified_at": item.get("timestamp"),
                "modified_by": item.get("editor_name") or "Unknown",
                "details": item.get("details") or {}
            })
            
        # Reverse to show newest version first
        formatted_history.reverse()
        return jsonify(formatted_history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
