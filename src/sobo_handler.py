import os
import logging
import unidecode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from uuid import uuid4

from .gemini_extractor import extract_land_certificate_with_gemini
from .email_utils import send_sobo_email_with_result
from .models import LandCertificateExtraction

logger = logging.getLogger(__name__)

# Các trạng thái
SOBO_DOC, SOBO_LOC, SOBO_SOURCE, SOBO_CONFIRM = range(20, 24)

# Danh sách Mapping
SOBO_MAPPING = {
    "Sobo.taynguyen@gmail.com": ["gia lai", "đắk lắk", "đăk lăk", "dak lak", "kon tum", "đắk nông", "đăk nông", "dak nong"],
    "Sobo.binhdinh@gmail.com": ["bình định", "binh dinh", "khánh hòa", "khanh hoa", "phú yên", "phu yen"],
    "Sobo.danang@gmail.com": ["đà nẵng", "da nang", "quảng ngãi", "quang ngai", "quảng nam", "quang nam", "huế", "hue", "thừa thiên huế", "quảng bình", "quang binh", "quảng trị", "quang tri"],
    "Sobohcm.cenvalue@gmail.com": ["hồ chí minh", "ho chi minh", "tp.hcm", "tphcm", "tây ninh", "tay ninh", "long an", "lâm đồng", "lam dong"],
    "Sobo.dongnai@gmail.com": ["đồng nai", "dong nai", "bình thuận", "binh thuan", "ninh thuận", "ninh thuan"],
    "Sobo.binhduong@gmail.com": ["bình dương", "binh duong", "bình phước", "binh phuoc", "bà rịa", "vũng tàu", "ba ria", "vung tau"],
    "Sobo.cantho@gmail.com": ["cần thơ", "can tho", "tiền giang", "tien giang", "bến tre", "ben tre", "vĩnh long", "vinh long", "trà vinh", "tra vinh", "hậu giang", "hau giang", "sóc trăng", "soc trang", "đồng tháp", "dong thap", "an giang", "kiên giang", "kien giang", "bạc liêu", "bac lieu", "cà mau", "ca mau"]
}

SIGNATURE_HTML = """
<br><br>
<div style="font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.5;">
    <span style="color: #1f497d;"><i>Trân trọng!</i></span><br>
    <span style="color: #e36c0a; font-size: 12pt;"><b>Phạm Ngọc Thanh Trường</b></span><br>
    <span style="color: #0070c0;"><b>Trưởng phòng kinh doanh khu vực Tây Nguyên</b></span><br>
    <span style="color: #0070c0;">Mobile: 0905.22.69.68 - 0913.503.051</span><br>
    <span style="color: #0070c0;">Email: <a href="mailto:truongpnt@cenvalue.vn" style="color: #0563c1;">truongpnt@cenvalue.vn</a></span><br>
    <span style="color: #1f497d;">***************************************************</span><br><br>
    <span style="color: #0070c0; font-size: 12pt;"><b>CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - CEN <span style="color: #e36c0a;">VALUE</span></b></span><br>
    <span style="color: #0070c0;"><u>Trụ sở chính</u></span><br>
    <span style="color: #0070c0;">Địa chỉ: Tầng 4, Tòa nhà Golden Palm, số 21 Lê Văn Lương, Nhân Chính, Thanh Xuân, Hà Nội</span><br>
    <span style="color: #0070c0;">Tel: (+8424) 32222 786 (Ext: 235) - Fax: (+8424) 32222 787</span><br>
    <span style="color: #0070c0;"><u>Chi nhánh tại Đà Nẵng</u></span><br>
    <span style="color: #0070c0;">Địa chỉ: Tầng 2, Số 06 Đường Trần Phú, Q. Hải Châu, Tp Đà Nẵng</span><br>
    <span style="color: #0070c0;">Tel: (0236) 3 65 66 61</span><br>
    <span style="color: #0070c0;">Website: <a href="http://www.thamdinhgiatheky.vn" style="color: #0563c1;">http://www.thamdinhgiatheky.vn</a></span>
</div>
"""

def find_department_email(address: str) -> str:
    if not address: return None
    addr_lower = address.lower()
    addr_norm = unidecode.unidecode(addr_lower)
    
    for email, provinces in SOBO_MAPPING.items():
        for prov in provinces:
            if prov.lower() in addr_lower or unidecode.unidecode(prov.lower()) in addr_norm:
                return email
    return None

async def cmd_sobo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Bắt đầu quy trình Gửi Sơ bộ*\n\n"
        "Vui lòng gửi **Ảnh chụp** hoặc **File PDF** Giấy chứng nhận quyền sử dụng đất để tôi quét thông tin Tỉnh/Thành phố và Thửa đất.",
        parse_mode="Markdown"
    )
    context.user_data['sobo'] = {}
    return SOBO_DOC

import asyncio
import fitz
from telegram.ext import ConversationHandler

async def sobo_receive_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.document:
        asyncio.create_task(_process_sobo_single_file(update, context, message.document, "pdf"))
        return SOBO_DOC
    elif message.photo:
        media_group_id = message.media_group_id
        if not media_group_id:
            asyncio.create_task(_process_sobo_single_file(update, context, message.photo[-1], "jpg"))
            return SOBO_DOC

        if "sobo_media_groups" not in context.bot_data:
            context.bot_data["sobo_media_groups"] = {}
        
        if media_group_id not in context.bot_data["sobo_media_groups"]:
            context.bot_data["sobo_media_groups"][media_group_id] = []
            asyncio.create_task(_wait_and_process_sobo_media_group(media_group_id, context))
        
        context.bot_data["sobo_media_groups"][media_group_id].append(update)
        return SOBO_DOC
            
    else:
        await update.message.reply_text("❌ Vui lòng gửi một tài liệu (PDF) hoặc hình ảnh (JPG/PNG).")
        return SOBO_DOC

async def _wait_and_process_sobo_media_group(media_group_id: str, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(1.5)
    updates = context.bot_data["sobo_media_groups"].pop(media_group_id, [])
    if updates:
        await _handle_sobo_media_group_photos(updates, context)

async def _process_sobo_single_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_ref, ext: str):
    file = await context.bot.get_file(file_ref.file_id)
    await update.message.reply_text("⏳ Đang tải và phân tích GCN bằng AI Gemini, vui lòng đợi giây lát...")
    
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"sobo_{uuid4().hex}.{ext}")
    await file.download_to_drive(file_path)
    
    return await _process_sobo_extracted_file(update, context, file_path)

async def _handle_sobo_media_group_photos(updates: list[Update], context: ContextTypes.DEFAULT_TYPE):
    first_update = updates[0]
    await first_update.message.reply_text(f"Đã nhận album gồm {len(updates)} ảnh. Đang ghép thành file PDF và quét bằng AI...")
    
    try:
        updates.sort(key=lambda u: u.message.message_id)
        image_paths = []
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        for i, up in enumerate(updates):
            photo = up.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            temp_path = os.path.join(upload_dir, f"sobo_part_{i}_{photo.file_unique_id}.jpg")
            await file.download_to_drive(temp_path)
            image_paths.append(temp_path)
            
        merged_pdf_path = os.path.join(upload_dir, f"sobo_merged_{uuid4().hex[:8]}.pdf")
        
        # Merge PDF
        doc = fitz.open()
        for img_path in image_paths:
            try:
                img_doc = fitz.open(img_path)
                pdf_bytes = img_doc.convert_to_pdf()
                img_doc.close()
                with fitz.open("pdf", pdf_bytes) as img_pdf:
                    doc.insert_pdf(img_pdf)
            except Exception:
                pass
        doc.save(merged_pdf_path)
        doc.close()
        
        for p in image_paths:
            try: os.remove(p)
            except: pass
            
        return await _process_sobo_extracted_file(first_update, context, merged_pdf_path)
        
    except Exception as exc:
        await first_update.message.reply_text(f"Xử lý album ảnh thất bại: {exc}")
        return SOBO_DOC

async def _process_sobo_extracted_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    try:
        api_key = os.getenv("GEMINI_API_KEY", "")
        model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        import asyncio
        from asyncio import to_thread
        extraction = await to_thread(extract_land_certificate_with_gemini, file_path, api_key=api_key, model=model_id)
        
        # Handle LandCertificateMultiExtraction
        if hasattr(extraction, "assets"):
            asset = extraction.assets[0] if extraction.assets else extraction
        elif hasattr(extraction, "assets"):
            asset = extraction.assets[0] if extraction.assets else extraction
        else:
            asset = extraction
        
        so_thua = asset.so_thua_dat.value.strip()
        so_to = asset.so_to_ban_do.value.strip()
        dia_chi = asset.dia_chi_thua_dat.value.strip()
        
        context.user_data['sobo']['so_thua'] = so_thua
        context.user_data['sobo']['so_to'] = so_to
        context.user_data['sobo']['dia_chi'] = dia_chi
        context.user_data['sobo']['file_path'] = file_path
        
        email = find_department_email(dia_chi)
        if email:
            context.user_data['sobo']['email'] = email
            email_info = f"✅ Đã nhận diện Tỉnh/Thành phố. Phòng ban phụ trách: **{email}**"
        else:
            context.user_data['sobo']['email'] = "Chưa xác định"
            email_info = "⚠️ Không thể tự động nhận diện Tỉnh/Thành phố. Vui lòng kiểm tra lại sau."

        await update.message.reply_text(
            f"Đã trích xuất thành công:\n"
            f"- Thửa: {so_thua}\n"
            f"- Tờ: {so_to}\n"
            f"- Địa chỉ: {dia_chi}\n\n"
            f"{email_info}\n\n"
            f"📍 Tiếp theo, vui lòng gửi **Link định vị tài sản** (Google Maps):",
            parse_mode="Markdown"
        )
        return SOBO_LOC
    except Exception as e:
        logger.error(f"Lỗi extract sơ bộ: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra trong quá trình nhận diện AI. Vui lòng gửi lại GCN rõ nét hơn.")
        return SOBO_DOC

async def sobo_receive_loc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc_link = update.message.text
    context.user_data['sobo']['link'] = loc_link
    
    await update.message.reply_text(
        "👤 Bước cuối cùng: Vui lòng nhập **Nguồn khách hàng** (Ví dụ: VCB Gia Lai, KH Cá nhân...)\n"
        "Điều này sẽ được ghi vào Tiêu đề Email."
    )
    return SOBO_SOURCE

async def sobo_receive_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: sobo_receive_source received: {update.message.text}")
    source = update.message.text
    sobo = context.user_data['sobo']
    sobo['source'] = source
    
    email = sobo.get('email')
    
    # Generate Preview
    subject = f"[SƠ BỘ] - {source} - Thửa đất số {sobo.get('so_thua')}, tờ bản đồ số {sobo.get('so_to')}; tại địa chỉ {sobo.get('dia_chi')}"
    body = f"Kính gửi anh chị,\n\nEm gửi tài sản tại Thửa đất số {sobo.get('so_thua')}, tờ bản đồ số {sobo.get('so_to')}; tại địa chỉ {sobo.get('dia_chi')}. Kính nhờ anh, chị hỗ trợ sơ bộ tài sản này giúp em nhé, Em cảm ơn!\n\nĐịnh vị ts: {sobo.get('link')}"
    
    body_html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 11pt;">
        <p>Kính gửi anh chị,</p>
        <p>Em gửi tài sản tại <b>Thửa đất số {sobo.get('so_thua')}, tờ bản đồ số {sobo.get('so_to')}; tại địa chỉ {sobo.get('dia_chi')}</b>. Kính nhờ anh, chị hỗ trợ sơ bộ tài sản này giúp em nhé, Em cảm ơn!</p>
        <p>Định vị ts: <a href="{sobo.get('link')}">{sobo.get('link')}</a></p>
    </div>
    """ + SIGNATURE_HTML
    
    sobo['subject'] = subject
    sobo['body'] = body
    sobo['body_html'] = body_html
    
    keyboard = [
        [InlineKeyboardButton("✅ Gửi Mail ngay", callback_data="sobo_send")],
        [InlineKeyboardButton("❌ Hủy bỏ", callback_data="sobo_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    import html
    preview_msg = (
        "📧 <b>BẢN XEM TRƯỚC EMAIL:</b>\n\n"
        f"<b>Người nhận:</b> {html.escape(str(email))}\n"
        f"<b>File đính kèm:</b> 1 file GCN\n"
        f"<b>Tiêu đề:</b> <code>{html.escape(subject)}</code>\n\n"
        f"<b>Nội dung:</b>\n{html.escape(body)}\n\n"
        "Bạn có muốn gửi mail này không?"
    )
    
    await update.message.reply_text(preview_msg, reply_markup=reply_markup, parse_mode="HTML")
    return SOBO_CONFIRM

async def sobo_handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "sobo_send":
        await query.edit_message_text("📨 Đang tiến hành gửi Mail...")
        sobo = context.user_data.get('sobo', {})
        email = sobo.get('email')
        subject = sobo.get('subject')
        body = sobo.get('body')
        body_html = sobo.get('body_html')
        file_path = sobo.get('file_path')
        
        # Bắt buộc phải có email gửi
        if email == "Chưa xác định" or not email:
            await query.edit_message_text("❌ Lỗi: Chưa xác định được Email phòng ban. Không thể gửi.")
            return ConversationHandler.END
            
        result = await send_sobo_email_with_result(
            email, 
            subject, 
            body, 
            html_body=body_html, 
            attachment_path=file_path,
            cc_emails=["bksdn@cenvalue.vn", "truongpnt@cenvalue.vn"]
        )
        
        if not result.success:
            await query.edit_message_text(f"Loi: {result.user_message}")
            return ConversationHandler.END

        if False:
            await query.edit_message_text(f"âŒ {result.user_message}")
            return ConversationHandler.END

        if result.success:
            await query.edit_message_text("✅ Đã gửi Email Yêu cầu Sơ bộ thành công!")
        else:
            await query.edit_message_text("❌ Việc gửi Email thất bại. Hãy kiểm tra lại tài khoản SMTP (MAIL_USERNAME, MAIL_PASSWORD) trong API.env.")
            
    else:
        await query.edit_message_text("🚫 Đã hủy yêu cầu Gửi Sơ bộ.")
        
    context.user_data.pop('sobo', None)
    return ConversationHandler.END

async def sobo_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Đã hủy thao tác Sơ bộ.", reply_markup=ReplyKeyboardRemove())
    context.user_data.pop('sobo', None)
    return ConversationHandler.END

def get_sobo_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler('sobo', cmd_sobo)],
        states={
            SOBO_DOC: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, sobo_receive_doc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_receive_loc)
            ],
            SOBO_LOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_receive_loc)],
            SOBO_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_receive_source)],
            SOBO_CONFIRM: [CallbackQueryHandler(sobo_handle_confirm, pattern="^sobo_")],
        },
        fallbacks=[CommandHandler('cancel', sobo_cancel_cmd)],
        per_message=False,
    )
