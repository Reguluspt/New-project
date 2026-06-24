from flask import Blueprint, request, jsonify, current_app, send_file
from api.middleware.auth import login_required
from pathlib import Path
import os
import io
import zipfile
import asyncio

from src.app_config import TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG
from src.template_manager import load_template_config, save_template_config
from src.oauth2_service import load_oauth_config, save_oauth_config, get_auth_url, exchange_code_for_tokens
from src.backup_service import create_backup

settings_bp = Blueprint("settings", __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def check_services_status():
    from src.background_services import _read_pid, _is_pid_running, DATA_DIR
    
    t_pid = _read_pid(PROJECT_ROOT / "telegram.pid")
    t_status = "running" if _is_pid_running(t_pid, "src.telegram_server:app") else "stopped"
    
    m_pid = _read_pid(DATA_DIR / "mail_listener.pid")
    m_status = "running" if _is_pid_running(m_pid, "src.mail_listener") else "stopped"
    
    n_pid = _read_pid(DATA_DIR / "ngrok.pid")
    n_status = "running" if _is_pid_running(n_pid, "ngrok") else "stopped"
    
    return {
        "telegram": t_status,
        "mail_listener": m_status,
        "ngrok": n_status
    }

@settings_bp.route("/settings", methods=["GET"])
@login_required
def get_settings_endpoint():
    db_path = current_app.config["SQLITE_DATABASE"]
    
    # 1. Paths
    template_config = load_template_config(TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG)
    paths = {
        "excel_template": template_config.get("excel_template_path", ""),
        "individual_template_dir": template_config.get("individual_template_dir", ""),
        "organization_template_dir": template_config.get("organization_template_dir", ""),
        "output_dir": str(PROJECT_ROOT / "outputs") # Default output dir
    }
    
    # 2. OAuth Connected status
    oauth_config = load_oauth_config()
    google_config = oauth_config.get("google", {})
    outlook_config = oauth_config.get("outlook", {})
    
    oauth = {
        "google": {
            "connected": bool(google_config.get("refresh_token")),
            "email": oauth_config.get("sobo_email", {}).get("mail_username") or google_config.get("client_id") or "",
            "client_id": google_config.get("client_id", ""),
            "client_secret": google_config.get("client_secret", "")
        },
        "outlook": {
            "connected": bool(outlook_config.get("refresh_token")),
            "email": outlook_config.get("sender_email") or "",
            "client_id": outlook_config.get("client_id", ""),
            "client_secret": outlook_config.get("client_secret", ""),
            "tenant": outlook_config.get("tenant", "common"),
            "sender_email": outlook_config.get("sender_email", "")
        },
        "redirect_uri": oauth_config.get("redirect_uri", "http://localhost:8501/"),
        "sobo_email": {
            "provider": oauth_config.get("sobo_email", {}).get("provider", "google") if isinstance(oauth_config.get("sobo_email"), dict) else "google",
            "mail_username": oauth_config.get("sobo_email", {}).get("mail_username", "hostktpro@gmail.com") if isinstance(oauth_config.get("sobo_email"), dict) else "hostktpro@gmail.com",
            "mail_from": oauth_config.get("sobo_email", {}).get("mail_from", "hostktpro@gmail.com") if isinstance(oauth_config.get("sobo_email"), dict) else "hostktpro@gmail.com"
        }
    }
    
    # 3. Background Services Status
    services = check_services_status()
    
    # 4. System Details
    db_size = "0.00 MB"
    if os.path.exists(db_path):
        size_bytes = os.path.getsize(db_path)
        db_size = f"{size_bytes / (1024 * 1024):.2f} MB"
        
    system = {
        "version": "2.0",
        "db_size": db_size
    }
    
    return jsonify({
        "paths": paths,
        "oauth": oauth,
        "services": services,
        "system": system
    })

@settings_bp.route("/settings/paths", methods=["PUT"])
@login_required
def update_settings_paths():
    data = request.get_json() or {}
    
    try:
        template_config = load_template_config(TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG)
        
        if "excel_template" in data:
            template_config["excel_template_path"] = data["excel_template"]
        if "individual_template_dir" in data:
            template_config["individual_template_dir"] = data["individual_template_dir"]
        if "organization_template_dir" in data:
            template_config["organization_template_dir"] = data["organization_template_dir"]
            
        save_template_config(TEMPLATE_CONFIG_PATH, template_config)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/oauth-config", methods=["PUT"])
@login_required
def update_oauth_config_endpoint():
    data = request.get_json() or {}
    try:
        oauth_config = load_oauth_config()
        
        # Google
        if "google" in data:
            g_data = data["google"]
            if "client_id" in g_data:
                oauth_config["google"]["client_id"] = g_data["client_id"].strip()
            if "client_secret" in g_data:
                oauth_config["google"]["client_secret"] = g_data["client_secret"].strip()
                
        # Outlook
        if "outlook" in data:
            o_data = data["outlook"]
            if "client_id" in o_data:
                oauth_config["outlook"]["client_id"] = o_data["client_id"].strip()
                oauth_config["outlook_smtp"]["client_id"] = o_data["client_id"].strip()
            if "client_secret" in o_data:
                oauth_config["outlook"]["client_secret"] = o_data["client_secret"].strip()
                oauth_config["outlook_smtp"]["client_secret"] = o_data["client_secret"].strip()
            if "tenant" in o_data:
                oauth_config["outlook"]["tenant"] = o_data["tenant"].strip() or "common"
                oauth_config["outlook_smtp"]["tenant"] = o_data["tenant"].strip() or "common"
            if "sender_email" in o_data:
                oauth_config["outlook"]["sender_email"] = o_data["sender_email"].strip()
                
        # Redirect URI
        if "redirect_uri" in data:
            oauth_config["redirect_uri"] = data["redirect_uri"].strip()
            
        # Sobo Email
        if "sobo_email" in data:
            s_data = data["sobo_email"]
            if not isinstance(oauth_config.get("sobo_email"), dict):
                oauth_config["sobo_email"] = {}
            if "provider" in s_data:
                oauth_config["sobo_email"]["provider"] = s_data["provider"].strip()
            if "mail_username" in s_data:
                oauth_config["sobo_email"]["mail_username"] = s_data["mail_username"].strip()
            if "mail_from" in s_data:
                oauth_config["sobo_email"]["mail_from"] = s_data["mail_from"].strip()

        save_oauth_config(oauth_config)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/oauth/<provider>/auth-url", methods=["GET"])
@login_required
def get_oauth_auth_url(provider):
    redirect_uri = request.args.get("redirect_uri", "http://localhost:5173/settings")
    try:
        auth_url = get_auth_url(provider, redirect_uri, state=provider)
        return jsonify({"url": auth_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/oauth/callback", methods=["POST"])
@login_required
def oauth_callback_endpoint():
    data = request.get_json() or {}
    provider = data.get("provider")
    code = data.get("code")
    redirect_uri = data.get("redirect_uri", "http://localhost:5173/settings")
    
    if not provider or not code:
        return jsonify({"error": "provider và code là bắt buộc"}), 400
        
    try:
        res = exchange_code_for_tokens(provider, code, redirect_uri)
        return jsonify({"success": True, "details": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/oauth/<provider>", methods=["DELETE"])
@login_required
def disconnect_oauth_endpoint(provider):
    try:
        config = load_oauth_config()
        if provider in config:
            config[provider]["access_token"] = ""
            config[provider]["refresh_token"] = ""
            config[provider]["expires_at"] = 0.0
            config[provider]["enabled"] = False
            
            # For outlook, also clear sender email and SMTP counterparts if needed
            if provider == "outlook":
                config["outlook"]["sender_email"] = ""
                if "outlook_smtp" in config:
                    config["outlook_smtp"]["access_token"] = ""
                    config["outlook_smtp"]["refresh_token"] = ""
                    config["outlook_smtp"]["expires_at"] = 0.0
                    config["outlook_smtp"]["enabled"] = False
                    
            save_oauth_config(config)
            return jsonify({"success": True})
        else:
            return jsonify({"error": f"Không tìm thấy provider: {provider}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/backup", methods=["POST"])
@login_required
def create_backup_endpoint():
    try:
        data_dir = PROJECT_ROOT / "data"
        backup_path = create_backup(data_dir)
        if not backup_path:
            return jsonify({"error": "Không thể tạo bản sao lưu"}), 500
            
        relative_path = str(backup_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        return jsonify({"backup_path": relative_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/backup/download", methods=["GET"])
@login_required
def download_backup_endpoint():
    try:
        backup_dir = PROJECT_ROOT / "data" / "backups"
        backups = sorted(backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime)
        
        if not backups:
            # Create a backup on-the-fly if none exist
            data_dir = PROJECT_ROOT / "data"
            backup_path = create_backup(data_dir)
            if not backup_path:
                return jsonify({"error": "Không có bản sao lưu nào để tải về"}), 404
            target_backup = backup_path
        else:
            target_backup = backups[-1]
            
        return send_file(target_backup, as_attachment=True, download_name=target_backup.name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/settings/backup/restore", methods=["POST"])
@login_required
def restore_backup_endpoint():
    if "file" not in request.files:
        return jsonify({"error": "Không có tệp phục hồi tải lên"}), 400
        
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tên tệp không hợp lệ"}), 400
        
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        file_bytes = file.read()
        
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zip_handle:
            names = zip_handle.namelist()
            essential = {"cases.db", "telegram_records.db"}
            if not any(name in essential for name in names):
                return jsonify({"error": "Tệp ZIP không chứa các cơ sở dữ liệu hợp lệ (cases.db hoặc telegram_records.db)"}), 400
                
            whitelist = {
                "cases.db",
                "telegram_records.db",
                "template_config.json",
                "ai_config.json",
                "case_table_config.json",
                "case_output_config.json"
            }
            
            for name in names:
                if name in whitelist:
                    zip_handle.extract(name, data_dir)
                    
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
