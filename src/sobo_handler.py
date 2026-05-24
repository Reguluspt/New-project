import os
import logging
import html
import unidecode
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from uuid import uuid4

from .gemini_extractor import extract_land_certificate_with_gemini
from .email_utils import send_sobo_email_with_result
from .models import LandCertificateExtraction

logger = logging.getLogger(__name__)

# Các trạng thái
(
    SOBO_ASSET_SELECT,
    SOBO_DOC,
    SOBO_LOC,
    SOBO_SOURCE,
    SOBO_CONFIRM,
    SOBO_MACHINERY_DOC,
    SOBO_MACHINERY_NAME,
    SOBO_MACHINERY_EMAIL,
) = range(20, 28)

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
SOBO_EMAIL_OPTIONS = tuple(SOBO_MAPPING.keys())
SOBO_ASSET_TYPE = "Quyền sử dụng đất và CTXD (nếu có hoàn công trên sổ)"


def build_sobo_email_content(sobo: dict) -> tuple[str, str]:
    source = str(sobo.get("source", ""))
    so_thua = str(sobo.get("so_thua", ""))
    so_to = str(sobo.get("so_to", ""))
    dia_chi = str(sobo.get("dia_chi", ""))
    link = str(sobo.get("link", ""))
    parsed_link = urlparse(link)
    href = link if parsed_link.scheme in {"http", "https"} else "#"

    body = (
        "Kính gửi Anh/Chị,\n\n"
        "Em gửi thông tin tài sản cần hỗ trợ tham khảo giá trị sơ bộ như sau:\n\n"
        "THÔNG TIN TÀI SẢN THẨM ĐỊNH\n"
        f"- Nguồn khách hàng: {source}\n"
        f"- Loại tài sản: {SOBO_ASSET_TYPE}\n"
        f"- Số thửa đất: {so_thua}\n"
        f"- Số tờ bản đồ: {so_to}\n"
        f"- Địa chỉ tài sản: {dia_chi}\n"
        f"- Định vị tài sản: {link}\n\n"
        "Kính nhờ Anh/Chị hỗ trợ sơ bộ tài sản nêu trên và phản hồi để "
        "Phòng Kinh Doanh tiếp tục làm việc với khách hàng.\n\n"
        "Trân trọng cảm ơn Anh/Chị.\n\n"
        "PHẠM NGỌC THANH TRƯỜNG\n"
        "Trưởng phòng Kinh Doanh Khu vực Tây Nguyên\n"
        "Công ty Cổ phần Thẩm định giá Thế Kỷ - CENVALUE\n"
        "Điện thoại: 0905 22 69 68 - 0913 503 051\n"
        "Email: truongpnt@cenvalue.vn"
    )

    safe_source = html.escape(source)
    safe_so_thua = html.escape(so_thua)
    safe_so_to = html.escape(so_to)
    safe_dia_chi = html.escape(dia_chi)
    safe_href = html.escape(href, quote=True)
    safe_asset_type = html.escape(SOBO_ASSET_TYPE)

    body_html = f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fb;margin:0;padding:20px 0;font-family:Arial,'Segoe UI',sans-serif;color:#11284d;">
  <tr>
    <td align="center">
      <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="width:100%;max-width:680px;background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
        <tr>
          <td style="padding:15px 28px;background:#ffffff;">
            <img src="cid:cenvalue_logo" width="170" alt="CENVALUE" style="display:block;width:170px;max-width:100%;height:auto;border:0;">
          </td>
        </tr>
        <tr>
          <td style="padding:19px 28px;background:#008e96;color:#ffffff;font-size:14px;font-weight:bold;line-height:1.4;">
            YÊU CẦU THAM KHẢO GIÁ TRỊ SƠ BỘ TÀI SẢN
          </td>
        </tr>
        <tr>
          <td style="padding:28px;font-size:15px;line-height:1.55;color:#283952;">
            <p style="margin:0 0 18px;">Kính gửi Anh/Chị,</p>
            <p style="margin:0 0 22px;">Em gửi thông tin tài sản cần hỗ trợ tham khảo giá trị sơ bộ như sau:</p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #cae4e5;border-radius:7px;overflow:hidden;font-size:14px;">
              <tr>
                <td colspan="2" style="padding:12px 16px;background:#eff9f9;color:#006a70;font-size:13px;font-weight:bold;">THÔNG TIN TÀI SẢN THẨM ĐỊNH</td>
              </tr>
              <tr><td width="180" style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Nguồn khách hàng</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;"><strong>{safe_source}</strong></td></tr>
              <tr><td style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Loại tài sản</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;">{safe_asset_type}</td></tr>
              <tr><td style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Số thửa đất</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;"><strong>{safe_so_thua}</strong></td></tr>
              <tr><td style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Số tờ bản đồ</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;"><strong>{safe_so_to}</strong></td></tr>
              <tr><td style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Địa chỉ tài sản</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;">{safe_dia_chi}</td></tr>
            </table>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;border:1px solid #e2e8f0;background:#f7fafc;border-radius:7px;">
              <tr>
                <td style="padding:14px 16px;">
                  <strong style="display:block;font-size:14px;color:#11284d;">Định vị tài sản</strong>
                  <span style="font-size:13px;color:#64748b;">Đường dẫn Google Maps từ quy trình /sobo</span>
                </td>
                <td align="right" style="padding:14px 16px;">
                  <a href="{safe_href}" style="display:inline-block;padding:10px 14px;border-radius:6px;background:#008e96;color:#ffffff;font-size:13px;font-weight:bold;text-decoration:none;">Xem vị trí tài sản</a>
                </td>
              </tr>
            </table>
            <p style="margin:0 0 18px;">Kính nhờ Anh/Chị hỗ trợ sơ bộ tài sản nêu trên và phản hồi để Phòng Kinh Doanh tiếp tục làm việc với khách hàng.</p>
            <p style="margin:0 0 24px;">Trân trọng cảm ơn Anh/Chị.</p>
            <div style="padding-top:20px;border-top:1px solid #e2e8f0;font-size:13px;line-height:1.5;color:#45566f;">
              <div style="font-size:16px;font-weight:bold;color:#006a70;">PHẠM NGỌC THANH TRƯỜNG</div>
              <div style="font-weight:bold;color:#d39a58;margin-bottom:6px;">Trưởng phòng Kinh Doanh Khu vực Tây Nguyên</div>
              <div>Công ty Cổ phần Thẩm định giá Thế Kỷ - CENVALUE</div>
              <div>Điện thoại: 0905 22 69 68 - 0913 503 051</div>
              <div>Email: <a href="mailto:truongpnt@cenvalue.vn" style="color:#006a70;text-decoration:none;">truongpnt@cenvalue.vn</a></div>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""
    return body, body_html


def build_machinery_email_content(sobo: dict) -> tuple[str, str]:
    equipment_name = str(sobo.get("equipment_name", ""))
    safe_name = html.escape(equipment_name)
    body = (
        "Kính gửi Anh/Chị,\n\n"
        "Em gửi thông tin tài sản cần hỗ trợ tham khảo giá trị sơ bộ như sau:\n\n"
        "THÔNG TIN TÀI SẢN THẨM ĐỊNH\n"
        "- Loại tài sản: Máy móc thiết bị\n"
        f"- Tên thiết bị: {equipment_name}\n\n"
        "Kính nhờ Anh/Chị hỗ trợ sơ bộ tài sản nêu trên và phản hồi để "
        "Phòng Kinh Doanh tiếp tục làm việc với khách hàng.\n\n"
        "Trân trọng cảm ơn Anh/Chị.\n\n"
        "PHẠM NGỌC THANH TRƯỜNG\n"
        "Trưởng phòng Kinh Doanh Khu vực Tây Nguyên\n"
        "Công ty Cổ phần Thẩm định giá Thế Kỷ - CENVALUE\n"
        "Điện thoại: 0905 22 69 68 - 0913 503 051\n"
        "Email: truongpnt@cenvalue.vn"
    )
    body_html = f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fb;margin:0;padding:20px 0;font-family:Arial,'Segoe UI',sans-serif;color:#11284d;">
  <tr>
    <td align="center">
      <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="width:100%;max-width:680px;background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
        <tr><td style="padding:15px 28px;background:#ffffff;"><img src="cid:cenvalue_logo" width="170" alt="CENVALUE" style="display:block;width:170px;max-width:100%;height:auto;border:0;"></td></tr>
        <tr><td style="padding:19px 28px;background:#008e96;color:#ffffff;font-size:14px;font-weight:bold;line-height:1.4;">YÊU CẦU THAM KHẢO GIÁ TRỊ SƠ BỘ TÀI SẢN</td></tr>
        <tr>
          <td style="padding:28px;font-size:15px;line-height:1.55;color:#283952;">
            <p style="margin:0 0 18px;">Kính gửi Anh/Chị,</p>
            <p style="margin:0 0 22px;">Em gửi thông tin tài sản cần hỗ trợ tham khảo giá trị sơ bộ như sau:</p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #cae4e5;border-radius:7px;overflow:hidden;font-size:14px;">
              <tr><td colspan="2" style="padding:12px 16px;background:#eff9f9;color:#006a70;font-size:13px;font-weight:bold;">THÔNG TIN TÀI SẢN THẨM ĐỊNH</td></tr>
              <tr><td width="180" style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Loại tài sản</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;">Máy móc thiết bị</td></tr>
              <tr><td style="padding:10px 16px;border-top:1px solid #edf2f8;color:#64748b;font-weight:bold;">Tên thiết bị</td><td style="padding:10px 16px;border-top:1px solid #edf2f8;"><strong>{safe_name}</strong></td></tr>
            </table>
            <p style="margin:22px 0 18px;">Kính nhờ Anh/Chị hỗ trợ sơ bộ tài sản nêu trên và phản hồi để Phòng Kinh Doanh tiếp tục làm việc với khách hàng.</p>
            <p style="margin:0 0 24px;">Trân trọng cảm ơn Anh/Chị.</p>
            <div style="padding-top:20px;border-top:1px solid #e2e8f0;font-size:13px;line-height:1.5;color:#45566f;">
              <div style="font-size:16px;font-weight:bold;color:#006a70;">PHẠM NGỌC THANH TRƯỜNG</div>
              <div style="font-weight:bold;color:#d39a58;margin-bottom:6px;">Trưởng phòng Kinh Doanh Khu vực Tây Nguyên</div>
              <div>Công ty Cổ phần Thẩm định giá Thế Kỷ - CENVALUE</div>
              <div>Điện thoại: 0905 22 69 68 - 0913 503 051</div>
              <div>Email: <a href="mailto:truongpnt@cenvalue.vn" style="color:#006a70;text-decoration:none;">truongpnt@cenvalue.vn</a></div>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""
    return body, body_html

def find_department_email(address: str) -> str:
    if not address: return None
    addr_lower = address.lower()
    addr_norm = unidecode.unidecode(addr_lower)
    
    for email, provinces in SOBO_MAPPING.items():
        for prov in provinces:
            if prov.lower() in addr_lower or unidecode.unidecode(prov.lower()) in addr_norm:
                return email
    return None


def build_department_email_keyboard(suggested_email: str | None) -> InlineKeyboardMarkup:
    keyboard = []
    for index, email in enumerate(SOBO_EMAIL_OPTIONS):
        prefix = "✅ " if email == suggested_email else "📧 "
        label = f"{prefix}{email}"
        if email == suggested_email:
            label += " (gợi ý)"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sobo_email_{index}")])
    keyboard.append([InlineKeyboardButton("❌ Hủy bỏ", callback_data="sobo_cancel")])
    return InlineKeyboardMarkup(keyboard)


def build_asset_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Bất động sản", callback_data="sobo_asset_real_estate")],
        [InlineKeyboardButton("⚙️ Máy móc thiết bị", callback_data="sobo_asset_machinery")],
        [InlineKeyboardButton("❌ Hủy bỏ", callback_data="sobo_cancel")],
    ])


async def cmd_sobo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Bắt đầu quy trình Gửi Sơ bộ*\n\n"
        "Vui lòng chọn **loại tài sản** cần gửi sơ bộ:",
        reply_markup=build_asset_type_keyboard(),
        parse_mode="Markdown",
    )
    context.user_data['sobo'] = {}
    return SOBO_ASSET_SELECT


async def sobo_select_asset_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['sobo'] = {}
    if query.data == "sobo_asset_real_estate":
        context.user_data['sobo']['asset_type'] = "real_estate"
        await query.edit_message_text(
            "🏠 Đã chọn Bất động sản.\n\n"
            "Vui lòng gửi Ảnh chụp hoặc File PDF Giấy chứng nhận quyền sử dụng đất "
            "để tôi quét thông tin Tỉnh/Thành phố và Thửa đất."
        )
        return SOBO_DOC

    if query.data != "sobo_asset_machinery":
        await query.edit_message_text("❌ Loại tài sản không hợp lệ. Vui lòng bắt đầu lại bằng /sobo.")
        context.user_data.pop('sobo', None)
        return ConversationHandler.END

    context.user_data['sobo']['asset_type'] = "machinery"
    await query.edit_message_text(
        "⚙️ Đã chọn Máy móc thiết bị.\n\n"
        "Vui lòng tải lên file hồ sơ hoặc hình ảnh thiết bị để đính kèm vào email. "
        "File sẽ không được quét hoặc phân tích."
    )
    return SOBO_MACHINERY_DOC

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


async def sobo_receive_machinery_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    filename = ""
    if message.document:
        file_ref = message.document
        filename = message.document.file_name or "ho_so_may_moc"
        extension = os.path.splitext(filename)[1].lower()
        if not extension or len(extension) > 10 or not extension[1:].isalnum():
            extension = ".bin"
    elif message.photo:
        file_ref = message.photo[-1]
        filename = "hinh_anh_may_moc.jpg"
        extension = ".jpg"
    else:
        await message.reply_text("❌ Vui lòng tải lên một file hồ sơ hoặc hình ảnh thiết bị.")
        return SOBO_MACHINERY_DOC

    file = await context.bot.get_file(file_ref.file_id)
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"sobo_machinery_{uuid4().hex}{extension}")
    await file.download_to_drive(file_path)

    sobo = context.user_data.setdefault('sobo', {})
    sobo['file_path'] = file_path
    sobo['attachment_name'] = filename
    await message.reply_text(
        "✅ Đã nhận file đính kèm. File không được quét hoặc phân tích.\n\n"
        "Vui lòng nhập *Tên thiết bị*:",
        parse_mode="Markdown",
    )
    return SOBO_MACHINERY_NAME


async def sobo_receive_machinery_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    equipment_name = update.message.text.strip()
    if not equipment_name:
        await update.message.reply_text("❌ Tên thiết bị không được để trống. Vui lòng nhập lại.")
        return SOBO_MACHINERY_NAME

    sobo = context.user_data.setdefault('sobo', {})
    sobo['equipment_name'] = equipment_name
    await update.message.reply_text(
        "📧 Vui lòng chọn *email nhận sơ bộ* từ danh sách dưới đây:",
        reply_markup=build_department_email_keyboard(None),
        parse_mode="Markdown",
    )
    return SOBO_MACHINERY_EMAIL


async def sobo_require_machinery_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 Vui lòng tải lên file hồ sơ hoặc hình ảnh thiết bị trước khi nhập tên thiết bị.")
    return SOBO_MACHINERY_DOC


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
        
        # Handle LandCertificateMultiExtraction and auto merge for multiple assets (hợp khối)
        if hasattr(extraction, "assets") and extraction.assets:
            if len(extraction.assets) > 1:
                thuas = []
                tos = []
                addresses = []
                for a in extraction.assets:
                    thua_val = a.so_thua_dat.value.strip() if a.so_thua_dat and a.so_thua_dat.value else ""
                    to_val = a.so_to_ban_do.value.strip() if a.so_to_ban_do and a.so_to_ban_do.value else ""
                    addr_val = a.dia_chi_thua_dat.value.strip() if a.dia_chi_thua_dat and a.dia_chi_thua_dat.value else ""
                    
                    if thua_val:
                        thuas.append(thua_val)
                    if to_val:
                        tos.append(to_val)
                    if addr_val:
                        addresses.append(addr_val)
                
                # Keep order and unique values
                unique_thuas = []
                for t in thuas:
                    if t not in unique_thuas:
                        unique_thuas.append(t)
                unique_tos = []
                for t in tos:
                    if t not in unique_tos:
                        unique_tos.append(t)
                
                so_thua = " + ".join(unique_thuas) if unique_thuas else ""
                so_to = " + ".join(unique_tos) if unique_tos else ""
                dia_chi = max(addresses, key=len) if addresses else ""
            else:
                asset = extraction.assets[0]
                so_thua = asset.so_thua_dat.value.strip()
                so_to = asset.so_to_ban_do.value.strip()
                dia_chi = asset.dia_chi_thua_dat.value.strip()
        else:
            asset = extraction
            so_thua = asset.so_thua_dat.value.strip()
            so_to = asset.so_to_ban_do.value.strip()
            dia_chi = asset.dia_chi_thua_dat.value.strip()
        
        context.user_data['sobo']['so_thua'] = so_thua
        context.user_data['sobo']['so_to'] = so_to
        context.user_data['sobo']['dia_chi'] = dia_chi
        context.user_data['sobo']['file_path'] = file_path
        
        suggested_email = find_department_email(dia_chi)
        if suggested_email:
            email_info = f"✅ Đã nhận diện Tỉnh/Thành phố. Email gợi ý: **{suggested_email}**"
        else:
            email_info = "⚠️ Không thể tự động nhận diện Tỉnh/Thành phố."
        context.user_data['sobo']['suggested_email'] = suggested_email
        context.user_data['sobo'].pop('email', None)

        await update.message.reply_text(
            f"Đã trích xuất thành công:\n"
            f"- Thửa: {so_thua}\n"
            f"- Tờ: {so_to}\n"
            f"- Địa chỉ: {dia_chi}\n\n"
            f"{email_info}\n\n"
            "📧 Vui lòng chọn **email nhận sơ bộ** từ danh sách dưới đây:",
            reply_markup=build_department_email_keyboard(suggested_email),
            parse_mode="Markdown",
        )
        return SOBO_DOC
    except Exception as e:
        logger.error(f"Lỗi extract sơ bộ: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra trong quá trình nhận diện AI. Vui lòng gửi lại GCN rõ nét hơn.")
        return SOBO_DOC


async def sobo_select_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        index = int(query.data.removeprefix("sobo_email_"))
        email = SOBO_EMAIL_OPTIONS[index]
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Lựa chọn email không hợp lệ. Vui lòng bắt đầu lại bằng /sobo.")
        context.user_data.pop('sobo', None)
        return ConversationHandler.END

    context.user_data.setdefault('sobo', {})['email'] = email
    if context.user_data['sobo'].get('asset_type') == "machinery":
        sobo = context.user_data['sobo']
        equipment_name = sobo.get('equipment_name', '')
        subject = f"[SƠ BỘ] - Máy móc thiết bị - {equipment_name}"
        body, body_html = build_machinery_email_content(sobo)
        sobo['subject'] = subject
        sobo['body'] = body
        sobo['body_html'] = body_html
        attachment_name = sobo.get('attachment_name', '1 file hồ sơ')
        preview_msg = (
            "📧 <b>BẢN XEM TRƯỚC EMAIL:</b>\n\n"
            f"<b>Người nhận:</b> {html.escape(str(email))}\n"
            f"<b>File đính kèm:</b> {html.escape(str(attachment_name))}\n"
            f"<b>Tiêu đề:</b> <code>{html.escape(subject)}</code>\n\n"
            f"<b>Nội dung:</b>\n{html.escape(body)}\n\n"
            "Bạn có muốn gửi mail này không?"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Gửi Mail ngay", callback_data="sobo_send")],
            [InlineKeyboardButton("❌ Hủy bỏ", callback_data="sobo_cancel")],
        ])
        await query.edit_message_text(preview_msg, reply_markup=reply_markup, parse_mode="HTML")
        return SOBO_CONFIRM

    await query.edit_message_text(
        f"✅ Đã chọn email nhận sơ bộ: {email}\n\n"
        "📍 Tiếp theo, vui lòng gửi Link định vị tài sản (Google Maps):"
    )
    return SOBO_LOC


async def sobo_require_email_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 Vui lòng chọn email nhận sơ bộ bằng nút phía trên trước khi gửi link định vị.")
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
    body, body_html = build_sobo_email_content(sobo)
    
    sobo['subject'] = subject
    sobo['body'] = body
    sobo['body_html'] = body_html
    
    keyboard = [
        [InlineKeyboardButton("✅ Gửi Mail ngay", callback_data="sobo_send")],
        [InlineKeyboardButton("❌ Hủy bỏ", callback_data="sobo_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
            SOBO_ASSET_SELECT: [
                CallbackQueryHandler(sobo_select_asset_type, pattern="^sobo_asset_"),
                CallbackQueryHandler(sobo_handle_confirm, pattern="^sobo_cancel$"),
            ],
            SOBO_DOC: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, sobo_receive_doc),
                CallbackQueryHandler(sobo_select_email, pattern="^sobo_email_"),
                CallbackQueryHandler(sobo_handle_confirm, pattern="^sobo_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_require_email_selection)
            ],
            SOBO_LOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_receive_loc)],
            SOBO_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_receive_source)],
            SOBO_MACHINERY_DOC: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, sobo_receive_machinery_doc),
                CallbackQueryHandler(sobo_handle_confirm, pattern="^sobo_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_require_machinery_file),
            ],
            SOBO_MACHINERY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobo_receive_machinery_name)],
            SOBO_MACHINERY_EMAIL: [
                CallbackQueryHandler(sobo_select_email, pattern="^sobo_email_"),
                CallbackQueryHandler(sobo_handle_confirm, pattern="^sobo_cancel$"),
            ],
            SOBO_CONFIRM: [CallbackQueryHandler(sobo_handle_confirm, pattern="^sobo_")],
        },
        fallbacks=[CommandHandler('cancel', sobo_cancel_cmd)],
        per_message=False,
    )
