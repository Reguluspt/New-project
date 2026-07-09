from flask import Blueprint, request, jsonify, current_app, send_file, after_this_request
from api.middleware.auth import login_required
from pathlib import Path
import uuid
import fitz
from PIL import Image
import io
import os
import shutil
import json

from src.sqlite_store import create_case, update_case
from src.case_files import case_folder
from src.app_config import CASE_FILES_DIR
from src.form_options_store import add_custom_form_option, merge_custom_form_options

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
entry_bp = Blueprint("entry", __name__)


def create_pdf_from_images(image_paths: list[Path], output_path: Path) -> int:
    document = fitz.open()
    try:
        for image_path in image_paths:
            image_doc = fitz.open(str(image_path))
            try:
                pdf_bytes = image_doc.convert_to_pdf()
            finally:
                image_doc.close()
            image_pdf = fitz.open("pdf", pdf_bytes)
            try:
                document.insert_pdf(image_pdf)
            finally:
                image_pdf.close()
        if len(document) == 0:
            return 0
        document.save(output_path)
        return len(document)
    finally:
        document.close()


def extract_selected_pages(original_pdf_path, pages_list):
    with fitz.open(original_pdf_path) as doc:
        new_doc = fitz.open()
        for p in pages_list:
            page_index = int(p) - 1
            if 0 <= page_index < len(doc):
                new_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)
        temp_dir = PROJECT_ROOT / "data" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_pdf_path = temp_dir / f"extract_{uuid.uuid4().hex}.pdf"
        new_doc.save(temp_pdf_path)
        new_doc.close()
        return temp_pdf_path

@entry_bp.route("/entry/upload", methods=["POST"])
@login_required
def upload_entry_files():
    if "files" not in request.files and "file" not in request.files:
        return jsonify({"error": "Không có file upload"}), 400
        
    files = request.files.getlist("files") or request.files.getlist("file")
    upload_id = str(uuid.uuid4())
    upload_dir = PROJECT_ROOT / "data" / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    response_files = []
    uploaded_image_pages: list[Path] = []
    for f in files:
        if not f.filename:
            continue
            
        file_id = uuid.uuid4().hex
        file_dir = upload_dir / file_id
        file_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(f.filename).name
        file_path = file_dir / filename
        f.save(file_path)
        
        suffix = file_path.suffix.lower()
        page_count = 0
        
        if suffix == ".pdf":
            try:
                with fitz.open(file_path) as doc:
                    page_count = len(doc)
                    for i in range(1, page_count + 1):
                        page = doc[i - 1]
                        matrix = fitz.Matrix(1.4, 1.4)
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        dest_path = file_dir / f"page_{i}.jpg"
                        pix.save(str(dest_path))
            except Exception as e:
                return jsonify({"error": f"Lỗi xử lý file PDF: {str(e)}"}), 500
        elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
            page_count = 1
            try:
                img = Image.open(file_path)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                image_page_path = file_dir / "page_1.jpg"
                img.save(image_page_path, format="JPEG", quality=90)
                uploaded_image_pages.append(image_page_path)
            except Exception as e:
                return jsonify({"error": f"Lỗi xử lý file ảnh: {str(e)}"}), 500
        else:
            continue
            
        thumbnails = [
            f"/api/entry/uploads/{upload_id}/{file_id}/page/{i}"
            for i in range(1, page_count + 1)
        ]
        
        response_files.append({
            "file_id": file_id,
            "name": filename,
            "pages": page_count,
            "thumbnails": thumbnails
        })

    if len(uploaded_image_pages) > 1:
        merged_file_id = uuid.uuid4().hex
        merged_dir = upload_dir / merged_file_id
        merged_dir.mkdir(parents=True, exist_ok=True)
        merged_path = merged_dir / "GCN_anh_ghep.pdf"
        try:
            page_count = create_pdf_from_images(uploaded_image_pages, merged_path)
            for i in range(1, page_count + 1):
                with fitz.open(merged_path) as doc:
                    page = doc[i - 1]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
                    pix.save(str(merged_dir / f"page_{i}.jpg"))
            response_files.insert(0, {
                "file_id": merged_file_id,
                "name": "GCN_anh_ghep.pdf",
                "pages": page_count,
                "thumbnails": [
                    f"/api/entry/uploads/{upload_id}/{merged_file_id}/page/{i}"
                    for i in range(1, page_count + 1)
                ],
                "merged_from_images": True,
            })
        except Exception as e:
            return jsonify({"error": f"Lỗi ghép ảnh GCN thành PDF: {str(e)}"}), 500

    return jsonify({
        "upload_id": upload_id,
        "files": response_files
    })

@entry_bp.route("/entry/uploads/<upload_id>/<file_id>/page/<int:page_num>", methods=["GET"])
def get_uploaded_page_image(upload_id, file_id, page_num):
    rotation = request.args.get("rotation", 0, type=int)
    upload_dir = PROJECT_ROOT / "data" / "uploads" / upload_id / file_id
    if not upload_dir.exists() or not upload_dir.is_dir():
        return jsonify({"error": "Không tìm thấy upload ID"}), 404
        
    img_path = None
    for ext in (".jpg", ".jpeg", ".png"):
        p = upload_dir / f"page_{page_num}{ext}"
        if p.exists():
            img_path = p
            break
            
    if not img_path:
        return jsonify({"error": "Không tìm thấy trang"}), 404
        
    try:
        img = Image.open(img_path)
        if rotation in (90, 180, 270):
            img = img.rotate(-rotation, expand=True)
            
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return send_file(buf, mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def merge_extractions(extractions):
    if not extractions:
        from src.models import blank_extraction
        if hasattr(blank_extraction(), "model_dump"):
            return blank_extraction().model_dump()
        return blank_extraction().dict()
        
    merged = {}
    fields = [
        "so_thua_dat",
        "so_to_ban_do",
        "dia_chi_thua_dat",
        "ten_chu_so_huu_cuoi_cung",
        "dia_chi_chu_so_huu_cuoi_cung",
        "so_cccd_chu_so_huu_cuoi_cung",
        "so_giay_chung_nhan",
        "so_vao_so_cap_giay_chung_nhan",
        "ngay_cap_giay_chung_nhan",
    ]
    
    for field in fields:
        merged[field] = {"value": "", "confidence": 0.0, "evidence": ""}
        
    merged["notes"] = []
    merged["page_metadata"] = []
    
    for ext in extractions:
        for field in fields:
            val = ext.get(field, {})
            if val and val.get("value"):
                curr = merged[field]
                if not curr["value"] or val.get("confidence", 0.0) > curr.get("confidence", 0.0):
                    merged[field] = {
                        "value": val.get("value", ""),
                        "confidence": val.get("confidence", 0.0),
                        "evidence": val.get("evidence", "")
                    }
        if "notes" in ext and isinstance(ext["notes"], list):
            for note in ext["notes"]:
                if note not in merged["notes"]:
                    merged["notes"].append(note)
        if "page_metadata" in ext and isinstance(ext["page_metadata"], list):
            merged["page_metadata"].extend(ext["page_metadata"])
            
    return merged

def append_certificate_info_notes(extraction: dict) -> dict:
    if not isinstance(extraction, dict):
        return extraction
    labels = [
        ("so_giay_chung_nhan", "Số giấy chứng nhận"),
        ("so_vao_so_cap_giay_chung_nhan", "Số vào sổ cấp giấy chứng nhận"),
        ("ngay_cap_giay_chung_nhan", "Ngày cấp giấy chứng nhận"),
    ]
    pending_notes = []
    for field, label in labels:
        raw_value = extraction.get(field) or {}
        value = raw_value.get("value") if isinstance(raw_value, dict) else raw_value
        value = str(value or "").strip()
        if not value:
            continue
        note = f"{label}: {value}"
        pending_notes.append(note)
    if not pending_notes:
        return extraction
    notes = extraction.setdefault("notes", [])
    if not isinstance(notes, list):
        notes = [str(notes)]
        extraction["notes"] = notes
    for note in pending_notes:
        if note not in notes:
            notes.append(note)
    return extraction


def find_original_upload_file(upload_dir: Path) -> Path | None:
    for item in upload_dir.iterdir():
        if item.is_file() and not item.name.startswith("page_"):
            return item
    return None


@entry_bp.route("/entry/extract", methods=["POST"])
@login_required
def extract_ocr_fields():
    data = request.get_json() or {}
    upload_id = data.get("upload_id")
    file_id = data.get("file_id")
    pages = data.get("pages", [1])
    provider = data.get("provider", "Gemini")
    model = data.get("model")
    extract_all = data.get("extract_all", False)
    
    if not file_id and not extract_all:
        return jsonify({"error": "Chưa chọn file để trích xuất"}), 400

    upload_dir_base = PROJECT_ROOT / "data" / "uploads" / upload_id
    if not upload_dir_base.exists() or not upload_dir_base.is_dir():
        return jsonify({"error": "Không tìm thấy upload ID"}), 404
        
    file_ids = []
    if extract_all:
        file_ids = [d.name for d in upload_dir_base.iterdir() if d.is_dir()]
        merged_image_ids = set()
        image_ids = set()
        for fid in file_ids:
            original = find_original_upload_file(upload_dir_base / fid)
            if not original:
                continue
            if original.name == "GCN_anh_ghep.pdf":
                merged_image_ids.add(fid)
            elif original.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                image_ids.add(fid)
        if merged_image_ids:
            file_ids = [fid for fid in file_ids if fid not in image_ids]
    else:
        file_ids = [file_id]

    if not file_ids:
        return jsonify({"error": "Không tìm thấy file để trích xuất"}), 400
        
    from src.app_config import load_ai_config, AI_CONFIG_PATH
    ai_config = load_ai_config(AI_CONFIG_PATH)
    
    prov_key = "Gemini" if provider.lower() == "gemini" else "OpenAI"
    prov_settings = ai_config.get("providers", {}).get(prov_key, {})
    
    api_key = prov_settings.get("api_key")
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") if prov_key == "Gemini" else os.getenv("OPENAI_API_KEY")
        
    if not api_key:
        return jsonify({"error": f"Chưa cấu hình API Key cho {prov_key}"}), 400
        
    if not model:
        model = prov_settings.get("model") or ("gemini-2.5-flash" if prov_key == "Gemini" else "gpt-4o-mini")
        
    extractions = []
    res_dicts = []
    
    for fid in file_ids:
        upload_dir = upload_dir_base / fid
        if not upload_dir.exists() or not upload_dir.is_dir():
            continue
            
        original_file = None
        for item in upload_dir.iterdir():
            if item.is_file() and not item.name.startswith("page_"):
                original_file = item
                break
                
        if not original_file:
            continue
            
        f_pages = pages
        if extract_all:
            if original_file.suffix.lower() == ".pdf":
                try:
                    with fitz.open(original_file) as doc:
                        f_pages = list(range(1, len(doc) + 1))
                except Exception:
                    f_pages = [1]
            else:
                f_pages = [1]
                
        extract_file = original_file
        if original_file.suffix.lower() == ".pdf":
            extract_file = extract_selected_pages(original_file, f_pages)
            
        try:
            if prov_key == "Gemini":
                from src.gemini_extractor import extract_land_certificate_with_gemini
                extraction = extract_land_certificate_with_gemini(extract_file, api_key=api_key, model=model)
            else:
                from src.extractor import extract_land_certificate
                extraction = extract_land_certificate(extract_file, api_key=api_key, model=model)
                
            if extract_file != original_file and extract_file.exists():
                extract_file.unlink()
                
            if hasattr(extraction, "model_dump"):
                res_dict = extraction.model_dump()
            else:
                res_dict = extraction.dict()
                
            assets = res_dict.get("assets", [])
            single_extraction = assets[0] if assets else {}
            extractions.append(single_extraction)
            res_dicts.append(res_dict)
        except Exception as e:
            if extract_file != original_file and extract_file.exists():
                try:
                    extract_file.unlink()
                except Exception:
                    pass
            if len(file_ids) == 1:
                return jsonify({"error": str(e)}), 500
            else:
                extractions.append({
                    "notes": [f"Lỗi trích xuất file {original_file.name}: {str(e)}"]
                })
                res_dicts.append({"assets": [{"notes": [f"Lỗi trích xuất file {original_file.name}: {str(e)}"]}]})
                
    if extract_all:
        merged = merge_extractions(extractions)
        append_certificate_info_notes(merged)
        return jsonify({
            "extraction": merged,
            "multi_extraction": {"assets": [merged]}
        })
    else:
        if extractions:
            append_certificate_info_notes(extractions[0])
        return jsonify({
            "extraction": extractions[0] if extractions else {},
            "multi_extraction": res_dicts[0] if res_dicts else {}
        })

@entry_bp.route("/entry/form-options", methods=["GET"])
@login_required
def entry_form_options():
    try:
        from src.app_config import TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG
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
        options = load_dropdown_options(excel_template_path)
        return jsonify(merge_custom_form_options(options))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@entry_bp.route("/entry/form-options/custom", methods=["POST"])
@login_required
def add_entry_form_option():
    data = request.get_json() or {}
    try:
        values = add_custom_form_option(data.get("field"), data.get("value"))
        return jsonify({"field": data.get("field"), "values": values})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@entry_bp.route("/entry/save", methods=["POST"])
@login_required
def save_entry_case():
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    extraction = data.get("extraction", {})
    case_type = data.get("case_type") or extraction.get("customer_type") or "individual"
    upload_id = data.get("upload_id")
    
    case_fields = dict(extraction)
    case_fields["customer_type"] = case_type
    
    try:
        case_id = create_case(db, case_fields)
        
        case_files_dir = current_app.config.get("CASE_FILES_DIR") or CASE_FILES_DIR
        folder = Path(case_folder(
            case_files_dir,
            case_id=case_id,
            contract_number=case_fields.get("contract_number") or "",
            customer_name=case_fields.get("customer_info") or "",
        ))
        
        original_file_path = ""
        if upload_id:
            upload_dir = PROJECT_ROOT / "data" / "uploads" / upload_id
            if upload_dir.exists() and upload_dir.is_dir():
                folder.mkdir(parents=True, exist_ok=True)
                for item in upload_dir.rglob("*"):
                    if item.is_file() and not item.name.startswith("page_"):
                        dest = folder / item.name
                        if dest.exists():
                            dest = folder / f"{item.parent.name[:8]}_{item.name}"
                        shutil.copy2(item, dest)
                        if not original_file_path:
                            original_file_path = str(dest)
                            
                try:
                    shutil.rmtree(upload_dir)
                except Exception:
                    pass
                    
        updates = {"case_folder": str(folder)}
        if original_file_path:
            updates["original_file_path"] = original_file_path
        update_case(db, case_id, updates)
        
        return jsonify({"case_id": case_id})
    except Exception as e:
        return jsonify({"error": f"Lỗi lưu hồ sơ: {str(e)}"}), 500

@entry_bp.route("/entry/excel-download", methods=["GET"])
@login_required
def download_excel_filled():
    try:
        from src.app_config import TEMPLATE_CONFIG_PATH, DEFAULT_TEMPLATE_CONFIG
        excel_template_path = Path(DEFAULT_TEMPLATE_CONFIG["excel_template_path"])
        if Path(TEMPLATE_CONFIG_PATH).exists():
            try:
                with open(TEMPLATE_CONFIG_PATH, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    if config_data.get("excel_template_path"):
                        excel_template_path = Path(config_data["excel_template_path"])
            except Exception:
                pass
                
        values = dict(request.args)
        
        temp_dir = PROJECT_ROOT / "data" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"filled_{uuid.uuid4().hex}.xlsx"
        
        from src.excel_writer import fill_template
        fill_template(excel_template_path, temp_file, values)
        
        @after_this_request
        def remove_file(response):
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
            return response
            
        return send_file(
            temp_file,
            as_attachment=True,
            download_name="form_nhap_lieu_dien.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@entry_bp.route("/entry/send-email", methods=["POST"])
@login_required
def send_entry_email_route():
    import asyncio
    from src.database_manager import create_outbound_tracking_record, resolve_records_db_path
    from src.mail_service import send_appraisal_email
    
    data = request.get_json() or {}
    payload = data.get("payload", {})
    
    try:
        records_db_path = Path(resolve_records_db_path())
        
        async def run_forwarding():
            record_id = await create_outbound_tracking_record(records_db_path, payload, file_path="desktop_entry")
            mail_payload = {**payload, "record_id": record_id, "records_db_path": str(records_db_path)}
            result = await send_appraisal_email(mail_payload)
            return result
        
        result = asyncio.run(run_forwarding())
        return jsonify({
            "success": True, 
            "to_email": result.to_email,
            "cc_emails": getattr(result, "cc_emails", [])
        })
    except Exception as e:
        return jsonify({"error": f"Gửi mail thất bại: {str(e)}"}), 500

@entry_bp.route("/entry/submit-web", methods=["POST"])
@login_required
def submit_entry_web_route():
    import asyncio
    from src.web_automation import run_company_web_entry, missing_web_entry_fields
    
    data = request.get_json() or {}
    payload = data.get("payload", {})
    
    missing = missing_web_entry_fields(payload)
    if missing:
        return jsonify({
            "error": "Thiếu thông tin bắt buộc để gửi Web.",
            "missing_fields": [{"label": item["label"], "source": item["source"]} for item in missing]
        }), 400
        
    try:
        async def run_web():
            result = await run_company_web_entry(payload, web_url="")
            return result
            
        result = asyncio.run(run_web())
        return jsonify({"success": True, "message": result})
    except Exception as e:
        return jsonify({"error": f"Nhập Web thất bại: {str(e)}"}), 500
