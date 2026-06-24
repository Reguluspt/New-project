from flask import Blueprint, request, jsonify, current_app, send_file
from api.middleware.auth import login_required
from pathlib import Path
from datetime import datetime
import mimetypes
import asyncio
import os

from src.sqlite_store import get_case, update_case
from src.case_files import case_folder
from src.app_config import (
    CASE_FILES_DIR,
    INDIVIDUAL_TEMPLATE_DIR,
    ORGANIZATION_TEMPLATE_DIR,
)

documents_bp = Blueprint("documents", __name__)

def ensure_delivery_columns(db_path):
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1] for row in cursor.fetchall()}
        if "delivery_contact_id" not in columns:
            cursor.execute("ALTER TABLE cases ADD COLUMN delivery_contact_id INTEGER")
        if "tracking_number" not in columns:
            cursor.execute("ALTER TABLE cases ADD COLUMN tracking_number TEXT")
        conn.commit()

def _case_with_organization_contact_address(export_case, db_path):
    if str(export_case.get("customer_type") or "").strip() != "organization" or db_path is None:
        return export_case

    query = str(export_case.get("tax_code") or export_case.get("customer_info") or "").strip()
    if not query:
        return export_case

    try:
        from src.sqlite_store import find_organization_by_query
        organizations = find_organization_by_query(db_path, query)
    except Exception:
        return export_case

    if not organizations:
        return export_case

    organization_address = str(organizations[0].get("address") or "").strip()
    if not organization_address:
        return export_case

    enriched_case = dict(export_case)
    enriched_case["customer_address"] = organization_address
    return enriched_case

def send_custom_email_with_attachments_sync(case, recipients, cc, subject, body, attachments, send_method="oauth2"):
    from email.message import EmailMessage
    from email.utils import make_msgid, parseaddr
    from src.mail_service import load_gmail_smtp_settings
    from src.oauth2_service import get_enabled_oauth_provider, get_valid_access_token_async, send_outlook_message_via_smtp_oauth2
    import requests
    import base64
    
    settings = load_gmail_smtp_settings()
    mail_from = settings.mail_from or settings.username or "appraisal@century.vn"
    
    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = ", ".join(recipients)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    
    domain = (parseaddr(mail_from)[1].split("@", 1)[1] if "@" in parseaddr(mail_from)[1] else "gmail.com")
    msg["Message-ID"] = make_msgid(domain=domain)
    
    msg.set_content(body)
    msg.add_alternative(body, subtype="html")
    
    case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
    folder = Path(case.get("case_folder") or case_folder(
        case_files_dir,
        case_id=case["id"],
        contract_number=case.get("contract_number") or "",
        customer_name=case.get("customer_info") or "",
    ))
    
    for filename in attachments:
        file_path = folder / filename
        if file_path.exists() and file_path.is_file():
            ctype, encoding = mimetypes.guess_type(str(file_path))
            if ctype is None or encoding:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)
            
    provider = get_enabled_oauth_provider()
    if provider and send_method == "oauth2":
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            access_token = loop.run_until_complete(get_valid_access_token_async(provider))
            if provider == "google":
                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                res = requests.post(url, headers=headers, json={"raw": raw})
                if res.status_code != 200:
                    raise RuntimeError(f"Gmail OAuth2 send error: {res.text}")
            elif provider == "outlook":
                loop.run_until_complete(send_outlook_message_via_smtp_oauth2(msg))
        finally:
            loop.close()
    else:
        from src.mail_service import _send_sync
        to_emails = [addr.strip() for addr in msg["To"].split(",") if addr.strip()]
        cc_emails = [addr.strip() for addr in msg["Cc"].split(",") if addr.strip()] if msg["Cc"] else []
        all_recipients = list(set(to_emails + cc_emails))
        _send_sync(msg, all_recipients, settings)

@documents_bp.route("/cases/<int:case_id>/documents/generate", methods=["POST"])
@login_required
def generate_documents(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    data = request.get_json() or {}
    payment_method = data.get("organization_contract_payment_method") or case.get("organization_contract_payment_method") or "standard"
    
    customer_type = case.get("customer_type") or "individual"
    if customer_type == "individual":
        templates_dir = INDIVIDUAL_TEMPLATE_DIR
    else:
        templates_dir = ORGANIZATION_TEMPLATE_DIR
        
    case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
    
    folder = Path(case.get("case_folder") or case_folder(
        case_files_dir,
        case_id=case_id,
        contract_number=case.get("contract_number") or "",
        customer_name=case.get("customer_info") or "",
    ))
    folder.mkdir(parents=True, exist_ok=True)
    
    update_case(db, case_id, {"case_folder": str(folder)})
    
    export_case = dict(case)
    export_case["case_folder"] = str(folder)
    if customer_type == "organization":
        export_case["organization_contract_payment_method"] = payment_method
        
    try:
        from src.case_exports import export_case_documents
        generated_paths = export_case_documents(
            export_case,
            customer_type=customer_type,
            templates_dir=templates_dir,
            case_files_dir=case_files_dir
        )
        
        documents_list = []
        for path in generated_paths:
            stat = path.stat()
            documents_list.append({
                "name": path.name,
                "type": path.suffix.lower().lstrip("."),
                "size": stat.st_size
            })
            
        return jsonify({"documents": documents_list})
    except Exception as e:
        return jsonify({"error": f"Xuất văn bản thất bại: {str(e)}"}), 500

@documents_bp.route("/cases/<int:case_id>/documents", methods=["GET"])
@login_required
def list_documents(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
    
    folder = Path(case.get("case_folder") or case_folder(
        case_files_dir,
        case_id=case_id,
        contract_number=case.get("contract_number") or "",
        customer_name=case.get("customer_info") or "",
    ))
    
    docs = []
    if folder.exists() and folder.is_dir():
        for item in folder.iterdir():
            if item.is_file():
                ext = item.suffix.lower().lstrip(".")
                stat = item.stat()
                created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
                docs.append({
                    "name": item.name,
                    "type": ext,
                    "size": stat.st_size,
                    "created_at": created_at
                })
    return jsonify(docs)

@documents_bp.route("/cases/<int:case_id>/documents/<string:filename>/preview", methods=["GET"])
@login_required
def preview_document(case_id, filename):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    customer_type = case.get("customer_type") or "individual"
    if customer_type == "individual":
        templates_dir = INDIVIDUAL_TEMPLATE_DIR
    else:
        templates_dir = ORGANIZATION_TEMPLATE_DIR
        
    case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
    
    from src.document_exporter import (
        describe_individual_documents,
        describe_organization_documents,
        render_docx_preview_html
    )
    
    if customer_type == "individual":
        descriptions = describe_individual_documents(case, templates_dir=templates_dir, case_files_dir=case_files_dir)
    else:
        export_case = dict(case)
        export_case["organization_contract_payment_method"] = "standard"
        descriptions = describe_organization_documents(export_case, templates_dir=templates_dir, case_files_dir=case_files_dir)
        if not any(Path(d["output_path"]).name.lower() == filename.lower() for d in descriptions):
            export_case["organization_contract_payment_method"] = "advance"
            descriptions = describe_organization_documents(export_case, templates_dir=templates_dir, case_files_dir=case_files_dir)
            
    matched = None
    for desc in descriptions:
        if Path(desc["output_path"]).name.lower() == filename.lower():
            matched = desc
            break
            
    if not matched:
        return jsonify({"error": f"Không tìm thấy template tương ứng với file {filename}"}), 404
        
    try:
        html_content = render_docx_preview_html(
            matched["template"],
            case,
            organization=(customer_type == "organization")
        )
        PRINT_CSS = """
<style>
@media print {
  @page { margin: 20mm 15mm; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 11pt; color: #000; }
  header, footer, .no-print, nav { display: none !important; }
  table { border-collapse: collapse; width: 100%; }
  td, th { border: 1px solid #000; padding: 4pt 6pt; }
  h1, h2, h3 { page-break-after: avoid; }
  img { max-width: 100%; }
}
</style>
"""
        # Inject print CSS before </head> if present, else prepend
        if "</head>" in html_content:
            html_content = html_content.replace("</head>", PRINT_CSS + "</head>", 1)
        else:
            html_content = PRINT_CSS + html_content
        return html_content, 200, {"Content-Type": "text/html; charset=utf-8"}

    except Exception as e:
        return jsonify({"error": f"Lỗi render preview: {str(e)}"}), 500

@documents_bp.route("/cases/<int:case_id>/documents/<string:filename>/download", methods=["GET"])
@login_required
def download_document(case_id, filename):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
    
    folder = Path(case.get("case_folder") or case_folder(
        case_files_dir,
        case_id=case_id,
        contract_number=case.get("contract_number") or "",
        customer_name=case.get("customer_info") or "",
    ))
    
    file_path = folder / filename
    try:
        if not file_path.resolve().is_relative_to(folder.resolve()):
            return jsonify({"error": "Đường dẫn không hợp lệ"}), 400
    except OSError:
        return jsonify({"error": "Đường dẫn không hợp lệ"}), 400
        
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"error": "Không tìm thấy file"}), 404
        
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename
    )

@documents_bp.route("/cases/<int:case_id>/documents/download-all", methods=["GET"])
@login_required
def download_all_documents(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
    
    folder = Path(case.get("case_folder") or case_folder(
        case_files_dir,
        case_id=case_id,
        contract_number=case.get("contract_number") or "",
        customer_name=case.get("customer_info") or "",
    ))
    
    if not folder.exists() or not folder.is_dir():
        return jsonify({"error": "Chưa có tài liệu nào được tạo để tải về"}), 400
        
    try:
        from src.case_exports import package_case_documents
        zip_path = package_case_documents(folder)
        if not zip_path.exists():
            return jsonify({"error": "Không thể tạo file nén ZIP"}), 500
            
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_path.name
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@documents_bp.route("/cases/<int:case_id>/documents/send-email", methods=["POST"])
@login_required
def send_email_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    data = request.get_json() or {}
    recipients = data.get("recipients", [])
    cc = data.get("cc", [])
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()
    attachments = data.get("attachments", [])
    send_method = data.get("send_method", "oauth2")
    
    if not recipients:
        return jsonify({"error": "Danh sách người nhận không được trống"}), 400
    if not subject:
        return jsonify({"error": "Tiêu đề không được trống"}), 400
    if not body:
        return jsonify({"error": "Nội dung email không được trống"}), 400
        
    try:
        send_custom_email_with_attachments_sync(
            case=case,
            recipients=recipients,
            cc=cc,
            subject=subject,
            body=body,
            attachments=attachments,
            send_method=send_method
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Gửi mail thất bại: {str(e)}"}), 500

@documents_bp.route("/cases/<int:case_id>/phathanh/reply", methods=["POST"])
@login_required
def send_phathanh_reply_endpoint(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    data = request.get_json() or {}
    certificate_number = data.get("certificate_number", "").strip()
    recipient = data.get("recipient", "").strip()
    
    updates = {}
    if certificate_number:
        updates["certificate_number"] = certificate_number
    updates["case_status"] = "Hoàn thành"
    updates["cancel_reason"] = ""
    
    try:
        update_case(db, case_id, updates)
    except Exception as e:
        return jsonify({"error": f"Không thể cập nhật trạng thái hồ sơ: {str(e)}"}), 500
        
    case = get_case(db, case_id)
    
    try:
        from src.email_reply_service import send_phathanh_email_for_case
        mail_case = _case_with_organization_contact_address(case, db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            to_email = loop.run_until_complete(send_phathanh_email_for_case(mail_case, recipient=recipient))
        finally:
            loop.close()
            
        return jsonify({"success": True, "to_email": to_email})
    except Exception as e:
        return jsonify({"error": f"Gửi mail phát hành thất bại: {str(e)}"}), 500

@documents_bp.route("/delivery/contacts", methods=["GET"])
@login_required
def get_delivery_contacts():
    try:
        from src.database_manager import resolve_records_db_path, ensure_tracking_record_schema, get_all_delivery_contacts
        records_db_path = Path(resolve_records_db_path())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(ensure_tracking_record_schema(records_db_path))
            contacts = loop.run_until_complete(get_all_delivery_contacts(records_db_path))
        finally:
            loop.close()
            
        result = []
        for c in contacts:
            result.append({
                "id": c.get("id"),
                "short_name": c.get("short_name"),
                "full_details": c.get("full_details")
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@documents_bp.route("/cases/<int:case_id>/delivery", methods=["POST"])
@documents_bp.route("/cases/<int:case_id>/documents/delivery", methods=["POST"])
@login_required
def save_case_delivery(case_id):
    db = current_app.config["SQLITE_DATABASE"]
    case = get_case(db, case_id)
    if not case:
        return jsonify({"error": "Không tìm thấy hồ sơ"}), 404
        
    data = request.get_json() or {}
    delivery_contact_id = data.get("delivery_contact_id")
    tracking_number = data.get("tracking_number", "").strip()
    
    ensure_delivery_columns(db)
    
    try:
        update_case(db, case_id, {
            "delivery_contact_id": delivery_contact_id,
            "tracking_number": tracking_number
        })
    except Exception as e:
        return jsonify({"error": f"Không thể cập nhật thông tin chuyển phát: {str(e)}"}), 500
        
    delivery_contact = None
    if delivery_contact_id:
        try:
            from src.database_manager import resolve_records_db_path
            import sqlite3
            records_db_path = resolve_records_db_path()
            with sqlite3.connect(records_db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM delivery_contacts WHERE id = ?", (delivery_contact_id,)).fetchone()
                if row:
                    delivery_contact = dict(row)
        except Exception:
            pass
            
    return jsonify({
        "success": True,
        "delivery_contact": delivery_contact,
        "tracking_number": tracking_number
    })
