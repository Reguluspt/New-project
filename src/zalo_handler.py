import os
import httpx
import logging
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from pathlib import Path
from uuid import uuid4

# Import các logic dùng chung từ hệ thống hiện tại
from .gemini_extractor import extract_land_certificate_with_gemini
from .database_manager import create_record_from_values, ensure_tracking_record_schema, resolve_records_db_path

router = APIRouter()
logger = logging.getLogger(__name__)

# Cấu hình
ZALO_BOT_PLATFORM_API = "https://bot-api.zaloplatforms.com/bot{token}/{method}"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploads")
RECORDS_DB = resolve_records_db_path(os.path.join(PROJECT_ROOT, "data", "telegram_records.db"))

def get_zalo_token() -> str:
    return os.getenv("ZALO_ACCESS_TOKEN", "").strip()

def get_gemini_config() -> tuple[str, str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    return key, model

async def call_zalo_api(method: str, payload: dict) -> dict:
    token = get_zalo_token()
    if not token:
        return {"ok": False, "description": "Token missing"}
    url = ZALO_BOT_PLATFORM_API.format(token=token, method=method)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
            return response.json()
        except Exception as e:
            logger.error(f"Lỗi Zalo API {method}: {e}")
            return {"ok": False, "description": str(e)}

async def send_zalo_message(chat_id: str, text: str) -> bool:
    result = await call_zalo_api("sendMessage", {"chat_id": chat_id, "text": text})
    ok = result.get("ok") is True
    if not ok:
        logger.error(f"sendMessage that bai cho chat_id={chat_id}: {result}")
    return ok

async def download_file(url: str, dest_path: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=60.0, follow_redirects=True)
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(response.content)
            return True
        except Exception as e:
            logger.error(f"Lỗi tải file từ Zalo: {e}")
            return False

def extraction_to_values(extraction) -> dict:
    """Chuyển đổi kết quả Gemini sang định dạng record database"""
    from .models import LandCertificateExtraction
    asset = extraction if isinstance(extraction, LandCertificateExtraction) else extraction.assets[0]

    so_thua = asset.so_thua_dat.value.strip()
    so_to = asset.so_to_ban_do.value.strip()
    dia_chi = asset.dia_chi_thua_dat.value.strip()
    chu_so_huu = asset.ten_chu_so_huu_cuoi_cung.value.strip()

    desc = f"Thửa {so_thua}, tờ {so_to}"
    if dia_chi:
        desc += f"; {dia_chi}"

    return {
        "so_thua": so_thua,
        "so_to": so_to,
        "dia_chi": dia_chi,
        "chu_so_huu": chu_so_huu,
        "customer_info": chu_so_huu,
        "asset_description": desc,
        "customer_type": "individual",
        "asset_type": "BĐS đặc thù khác",
        "preliminary_status": "Chưa sơ bộ",
    }


async def handle_zalo_image(chat_id: str, photo_url: str):
    """Xử lý ảnh GCN từ Zalo: Tải về -> Quét AI -> Lưu DB -> Phản hồi"""
    await send_zalo_message(chat_id, "⚙️ Đang tải ảnh và phân tích bằng AI Gemini, vui lòng đợi giây lát...")

    # 1. Tải ảnh
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"zalo_{uuid4().hex}.jpg")
    if not await download_file(photo_url, file_path):
        await send_zalo_message(chat_id, "❌ Lỗi: Không thể tải ảnh từ Zalo.")
        return

    # 2. Quét bằng Gemini
    api_key, model = get_gemini_config()
    try:
        extraction = await asyncio.to_thread(
            extract_land_certificate_with_gemini,
            file_path,
            api_key=api_key,
            model=model,
        )

        # 3. Lưu Database
        values = extraction_to_values(extraction)
        await ensure_tracking_record_schema(RECORDS_DB)
        record_id = await create_record_from_values(
            RECORDS_DB, values, file_path=file_path, status="PENDING"
        )

        # 4. Phản hồi
        summary = (
            f"✅ Đã quét GCN và lưu bản ghi #{record_id} thành công!\n\n"
            f"📍 Số thửa: {values['so_thua']}\n"
            f"📍 Số tờ: {values['so_to']}\n"
            f"🏠 Địa chỉ: {values['dia_chi']}\n"
            f"👤 Chủ sở hữu: {values['chu_so_huu']}\n\n"
            f"Bạn có thể kiểm tra trên phần mềm chính."
        )
        await send_zalo_message(chat_id, summary)

    except Exception as e:
        logger.error(f"Lỗi xử lý ảnh GCN trên Zalo: {e}")
        await send_zalo_message(chat_id, f"❌ Lỗi AI: {str(e)}")


async def process_zalo_webhook(data: dict) -> None:
    """
    Xử lý webhook từ Zalo Bot Creator.
    
    Zalo Bot Creator gửi dữ liệu theo 2 định dạng có thể:
    - Trực tiếp: {"event_name": "...", "message": {...}}
    - Bọc result: {"ok": true, "result": {"event_name": "...", "message": {...}}}
    """
    # Tương thích cả 2 định dạng
    if "result" in data and isinstance(data["result"], dict):
        payload = data["result"]
    else:
        payload = data

    event_name = payload.get("event_name")
    message = payload.get("message", {})
    chat_id = message.get("chat", {}).get("id")

    logger.info(f"Zalo webhook: event={event_name}, chat_id={chat_id}")

    if not chat_id:
        logger.warning(f"Zalo webhook: khong tim thay chat_id trong payload: {data}")
        return

    # 1. Tin nhắn văn bản
    if event_name == "message.text.received":
        text = message.get("text", "")
        logger.info(f"Zalo Text tu {chat_id}: {text}")

        lower_text = text.lower().strip()
        if lower_text in ("start", "/start", "chào", "chao", "hi", "hello", "xin chào"):
            await send_zalo_message(
                chat_id,
                "👋 Xin chào! Tôi là Bot thẩm định.\n\n"
                "📷 Gửi ảnh Giấy chứng nhận (GCN) để tôi tự động quét thông tin.\n"
                "📄 Hoặc gửi file PDF để xử lý.\n\n"
                "Hãy thử ngay!",
            )
        else:
            await send_zalo_message(
                chat_id,
                f"📩 Bot đã nhận tin nhắn: \"{text}\"\n\n"
                "Hãy gửi ảnh hoặc PDF Giấy chứng nhận để tôi quét giúp bạn!",
            )

    # 2. Tin nhắn hình ảnh
    elif event_name == "message.image.received":
        logger.info(f"Zalo Image tu {chat_id}")
        # Zalo Bot Creator gửi URL ảnh trong trường "photo_url" (chuỗi đơn)
        photo_url = message.get("photo_url", "")
        if photo_url:
            await handle_zalo_image(chat_id, photo_url)
        else:
            await send_zalo_message(chat_id, "❌ Không tìm thấy URL ảnh trong tin nhắn.")

    # 3. Tin nhắn không hỗ trợ (PDF, file...)
    elif event_name == "message.unsupported.received":
        await send_zalo_message(
            chat_id,
            "⚠️ Định dạng tin nhắn này chưa được hỗ trợ.\n"
            "Vui lòng gửi ảnh chụp (không phải file đính kèm) Giấy chứng nhận để tôi quét giúp bạn.",
        )

    else:
        logger.info(f"Zalo webhook: su kien khong xu ly: {event_name}")


@router.post("/webhook/zalo")
async def zalo_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    try:
        # Kiểm tra Secret Token nếu đã cấu hình
        expected_secret = os.getenv("ZALO_WEBHOOK_SECRET", "").strip()
        if expected_secret:
            if request.headers.get("X-Bot-Api-Secret-Token") != expected_secret:
                logger.warning("Zalo Webhook: Secret Token khong khop!")
                return {"ok": False, "description": "Unauthorized"}

        payload = await request.json()
        logger.info(f"Zalo Webhook payload received: {list(payload.keys())}")
        background_tasks.add_task(process_zalo_webhook, payload)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Lỗi Zalo Webhook: {e}")
        return {"ok": False}
