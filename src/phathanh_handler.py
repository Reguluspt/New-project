
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from .database_manager import get_case_by_contract_number, get_record_by_contract_number, search_delivery_contacts
from .contracts import expand_contract_number
import os
from pathlib import Path

# States
PHATHANH_WAIT_CONTRACT = 1
PHATHANH_CONFIRM_CUSTOMER = 2
PHATHANH_WAIT_RECIPIENT_QUERY = 3
PHATHANH_CHOOSE_RECIPIENT = 4
PHATHANH_EDIT_FIELD_SELECT = 5
PHATHANH_EDIT_FIELD_INPUT = 6


def _build_customer_confirmation(record):
    """Build confirmation message and keyboard for customer info."""
    c_type = "Cá nhân" if record.get("customer_type") == "individual" else "Tổ chức"
    msg = (
        f"✅ **Thông tin hồ sơ:**\n\n"
        f"1. Loại khách hàng: {c_type}\n"
        f"2. Tên: {record.get('customer_info', record.get('owner_name', 'N/A'))}\n"
        f"3. Địa chỉ: {record.get('customer_address', record.get('dia_chi_thua_dat', 'N/A'))}\n"
    )
    if record.get("customer_type") == "individual":
        msg += f"4. Số CCCD: {record.get('citizen_id', 'Chưa có')}\n"

    msg += "\nAnh xác nhận thông tin trên là đúng chứ ạ?"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Đúng, tiếp tục", callback_data="confirm_customer")],
        [InlineKeyboardButton("✏️ Sửa thông tin", callback_data="edit_customer")],
        [InlineKeyboardButton("❌ Hủy bỏ", callback_data="cancel")]
    ])
    return msg, keyboard


async def start_phathanh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🚀 **Luồng Phát hành chứng thư**\n\n"
        "Anh vui lòng nhập **Số hợp đồng** (ví dụ: .0881 hoặc 010/2026/N05.0881/DN):",
        parse_mode="Markdown"
    )
    return PHATHANH_WAIT_CONTRACT

async def handle_contract_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contract_query = update.message.text.strip()
    expanded = expand_contract_number(contract_query)
    
    # 1. Tìm trong cases.db (Phần mềm)
    cases_db = os.getenv("TELEGRAM_CASES_DB", os.getenv("SQLITE_DATABASE", "data/cases.db"))
    record = await get_case_by_contract_number(cases_db, expanded)
    
    # 2. Dự phòng tìm trong records.db (Bot)
    if not record:
        records_db = os.getenv("RECORDS_DB_PATH", "data/telegram_records.db")
        record = await get_record_by_contract_number(records_db, expanded)
    
    if not record:
        await update.message.reply_text(f"❌ Không tìm thấy hồ sơ với số hợp đồng: {expanded}. Anh vui lòng kiểm tra lại hoặc nhập số khác:")
        return PHATHANH_WAIT_CONTRACT

    # Lưu record vào context
    context.user_data["phathanh_record"] = record
    
    # Hiển thị thông tin xác nhận
    msg, keyboard = _build_customer_confirmation(record)
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")
    return PHATHANH_CONFIRM_CUSTOMER

async def confirm_customer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_customer":
        # Chuyển sang bước chọn người nhận
        default_recipient = (
            "CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - VP TẠI GIA LAI\n"
            "Địa chỉ: 90/60/3 Trường Chinh, phường Pleiku, tỉnh Gia Lai\n"
            "Điện thoại 0905226968"
        )
        context.user_data["phathanh_recipient"] = default_recipient
        
        msg = (
            "📌 **Bước 3: Thông tin người nhận hồ sơ**\n\n"
            "Người nhận mặc định:\n"
            f"_{default_recipient}_\n\n"
            "Anh có muốn giữ nguyên hay tìm người nhận khác trong danh bạ?"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Giữ nguyên", callback_data="keep_default_recipient")],
            [InlineKeyboardButton("🔍 Tìm trong danh bạ", callback_data="search_recipient")],
            [InlineKeyboardButton("❌ Hủy", callback_data="cancel")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return PHATHANH_WAIT_RECIPIENT_QUERY
    elif query.data == "edit_customer":
        record = context.user_data.get("phathanh_record", {})
        keyboard = [
            [InlineKeyboardButton("📝 Sửa Tên", callback_data="edit_field_customer_info")],
            [InlineKeyboardButton("📍 Sửa Địa chỉ", callback_data="edit_field_customer_address")],
        ]
        if record.get("customer_type") == "individual":
            keyboard.append([InlineKeyboardButton("🪪 Sửa số CCCD", callback_data="edit_field_citizen_id")])
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_confirm")])

        await query.edit_message_text(
            "✏️ **Chọn thông tin cần sửa:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return PHATHANH_EDIT_FIELD_SELECT
    else:
        await query.edit_message_text("Đã hủy luồng phát hành.")
        return ConversationHandler.END

async def wait_for_recipient_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == "keep_default_recipient":
            # Xử lý gửi mail ở đây hoặc chuyển sang bước cuối
            return await finalize_phathanh(update, context)
        elif query.data == "search_recipient":
            await query.edit_message_text("Anh vui lòng nhập tên gợi nhớ (cột trái) để tìm người nhận:")
            return PHATHANH_CHOOSE_RECIPIENT
    return PHATHANH_WAIT_RECIPIENT_QUERY

async def handle_recipient_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    search_query = update.message.text.strip()
    records_db = os.getenv("RECORDS_DB_PATH", "data/telegram_records.db")
    matches = await search_delivery_contacts(records_db, search_query)
    
    if not matches:
        await update.message.reply_text(f"❌ Không tìm thấy '{search_query}' trong danh bạ. Anh vui lòng nhập từ khóa khác:")
        return PHATHANH_CHOOSE_RECIPIENT
    
    context.user_data["phathanh_matches"] = matches
    
    msg = f"🔍 Tìm thấy {len(matches)} kết quả. Anh vui lòng chọn số thứ tự:\n\n"
    for i, m in enumerate(matches, 1):
        msg += f"{i}. {m['short_name']}\n"
    
    await update.message.reply_text(msg)
    return PHATHANH_CHOOSE_RECIPIENT

async def handle_recipient_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    matches = context.user_data.get("phathanh_matches", [])
    
    is_number = False
    try:
        idx = int(text) - 1
        is_number = True
    except ValueError:
        pass
        
    if is_number:
        if 0 <= idx < len(matches):
            selected = matches[idx]
            context.user_data["phathanh_recipient"] = selected["full_details"]
            await update.message.reply_text(f"✅ Đã chọn: {selected['short_name']}\n\nThông tin chi tiết:\n_{selected['full_details']}_", parse_mode="Markdown")
            return await finalize_phathanh(update, context)
        else:
            await update.message.reply_text("Số thứ tự không hợp lệ. Anh vui lòng chọn lại:")
            return PHATHANH_CHOOSE_RECIPIENT
    else:
        # Nếu không nhập số, coi như tìm kiếm lại
        return await handle_recipient_search(update, context)

async def finalize_phathanh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from .email_reply_service import find_latest_email_by_subject, send_phathanh_reply
    from .mail_service import load_gmail_smtp_settings
    from datetime import datetime, timedelta
    
    record = context.user_data.get("phathanh_record")
    recipient = context.user_data.get("phathanh_recipient")
    contract_number = record.get("contract_number")
    
    msg_status = await (update.callback_query.message if update.callback_query else update.message).reply_text(
        f"⏳ Đang tìm luồng mail cho hợp đồng {contract_number}..."
    )
    
    # 1. Tìm mail cũ
    original_mail = await find_latest_email_by_subject(contract_number)
    if not original_mail:
        await msg_status.edit_text(f"❌ Không tìm thấy email nào có tiêu đề chứa số hợp đồng: {contract_number}. Anh vui lòng kiểm tra lại hộp thư hoặc gửi mail đầu tiên trước ạ.")
        return ConversationHandler.END
        
    await msg_status.edit_text("📧 Đã tìm thấy luồng mail. Đang tạo nội dung phát hành...")
    
    # 2. Chuẩn bị dữ liệu HTML
    template_path = Path(__file__).parent / "templates" / "phathanh_template.html"
    if not template_path.exists():
        template_path = Path("src/templates/phathanh_template.html")
    if not template_path.exists():
        await msg_status.edit_text("❌ Thiếu file template: src/templates/phathanh_template.html")
        return ConversationHandler.END
        
    html_template = template_path.read_text(encoding="utf-8")
    
    # Tính toán ngày
    now = datetime.now()
    date_receive = (now + timedelta(days=1)).strftime("%d/%m/%Y")
    date_payment = now.strftime("%d/%m/%Y")
    
    # Lấy chữ ký từ môi trường
    signature = os.getenv("MAIL_SIGNATURE", "Trân trọng,<br>Century Appraisal")
    
    # Xử lý thông tin cá nhân/tổ chức
    customer_extra_html = ""
    if record.get("customer_type") == "individual":
        citizen_id = record.get('citizen_id')
        if citizen_id:
            customer_extra_html = f'<br><i style="color: #7f8c8d; font-size: 12px;">(CCCD: {citizen_id})</i>'
            
    # Bold the labels "Địa chỉ" and "Điện thoại" in recipient details
    from src.email_utils import format_recipient_info
    recipient_clean = format_recipient_info(recipient)
    recipient_html = recipient_clean.replace("\n", "<br>")
    if "Địa chỉ:" in recipient_html:
        recipient_html = recipient_html.replace("Địa chỉ:", "<strong>Địa chỉ:</strong>")
    elif "Địa chỉ" in recipient_html:
        recipient_html = recipient_html.replace("Địa chỉ", "<strong>Địa chỉ</strong>")
        
    if "Điện thoại:" in recipient_html:
        recipient_html = recipient_html.replace("Điện thoại:", "<strong>Điện thoại:</strong>")
    elif "Điện thoại" in recipient_html:
        recipient_html = recipient_html.replace("Điện thoại", "<strong>Điện thoại</strong>")
    
    replacements = {
        "{{ customer_name }}": record.get("customer_info", record.get("owner_name", "N/A")),
        "{{ customer_address }}": record.get("customer_address", record.get("dia_chi_thua_dat", "N/A")),
        "{{ customer_extra_html }}": customer_extra_html,
        "{{ recipient_info }}": recipient_html,
        "{{ date_receive }}": date_receive,
        "{{ date_payment }}": date_payment,
        "{{ personal_note }}": "",
        "{{ email_signature }}": signature
    }
    
    html_body = html_template
    for placeholder, value in replacements.items():
        html_body = html_body.replace(placeholder, str(value))
        
    # 3. Gửi mail
    settings = load_gmail_smtp_settings()
    success = await send_phathanh_reply(original_mail, html_body, settings)
    
    if success:
        await msg_status.edit_text(
            f"✅ **Đã gửi mail phát hành thành công!**\n\n"
            f"📍 Trả lời mail: _{original_mail['subject']}_\n"
            f"📍 Người nhận: {original_mail['from']}\n"
            f"📍 Đồng gửi: {original_mail['cc'] or 'Không có'}",
            parse_mode="Markdown"
        )
    else:
        await msg_status.edit_text("❌ Lỗi khi gửi mail. Anh vui lòng kiểm tra cấu hình SMTP/Password ứng dụng nhé.")
    
    return ConversationHandler.END


async def edit_field_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field selection for editing customer info."""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_confirm":
        record = context.user_data.get("phathanh_record", {})
        msg, keyboard = _build_customer_confirmation(record)
        await query.edit_message_text(msg, reply_markup=keyboard, parse_mode="Markdown")
        return PHATHANH_CONFIRM_CUSTOMER

    field_map = {
        "edit_field_customer_info": ("customer_info", "Tên khách hàng"),
        "edit_field_customer_address": ("customer_address", "Địa chỉ"),
        "edit_field_citizen_id": ("citizen_id", "Số CCCD"),
    }

    if query.data in field_map:
        field_key, field_label = field_map[query.data]
        context.user_data["phathanh_editing_field"] = field_key
        record = context.user_data.get("phathanh_record", {})
        current_value = record.get(field_key, "Chưa có")

        await query.edit_message_text(
            f"✏️ **Sửa {field_label}**\n\n"
            f"Giá trị hiện tại: _{current_value}_\n\n"
            f"Anh vui lòng nhập giá trị mới:",
            parse_mode="Markdown"
        )
        return PHATHANH_EDIT_FIELD_INPUT

    return PHATHANH_EDIT_FIELD_SELECT


async def edit_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new value input for the selected field."""
    new_value = update.message.text.strip()
    field_key = context.user_data.pop("phathanh_editing_field", None)

    if not field_key:
        await update.message.reply_text("❌ Lỗi: không xác định được trường cần sửa. Vui lòng thử lại.")
        return PHATHANH_CONFIRM_CUSTOMER

    # Update record in context
    record = context.user_data.get("phathanh_record", {})
    record[field_key] = new_value
    context.user_data["phathanh_record"] = record

    field_labels = {
        "customer_info": "Tên khách hàng",
        "customer_address": "Địa chỉ",
        "citizen_id": "Số CCCD",
    }
    label = field_labels.get(field_key, field_key)

    # Re-show confirmation with updated info
    msg, keyboard = _build_customer_confirmation(record)
    await update.message.reply_text(
        f"✅ Đã cập nhật _{label}_ → `{new_value}`\n\n{msg}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return PHATHANH_CONFIRM_CUSTOMER


async def cancel_phathanh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 Đã hủy luồng phát hành.")
    return ConversationHandler.END


def get_phathanh_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("phathanh", start_phathanh)],
        states={
            PHATHANH_WAIT_CONTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contract_input)],
            PHATHANH_CONFIRM_CUSTOMER: [CallbackQueryHandler(confirm_customer_callback)],
            PHATHANH_EDIT_FIELD_SELECT: [CallbackQueryHandler(edit_field_select_callback)],
            PHATHANH_EDIT_FIELD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_input)],
            PHATHANH_WAIT_RECIPIENT_QUERY: [CallbackQueryHandler(wait_for_recipient_query)],
            PHATHANH_CHOOSE_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipient_selection)],
        },
        fallbacks=[CommandHandler("cancel", cancel_phathanh)],
    )
