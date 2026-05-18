from __future__ import annotations

import os
import re
import smtplib
import subprocess
import sys
import unicodedata
import asyncio
from asyncio import create_task
from asyncio import to_thread
from contextlib import asynccontextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import AsyncIterator
from uuid import uuid4

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from telegram import Document, InlineKeyboardButton, InlineKeyboardMarkup, PhotoSize, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .gemini_extractor import extract_land_certificate_with_gemini
from .contracts import short_contract_number
from .excel_writer import load_dropdown_options
from .mail_renderer import mail_data_from_record, render_appraisal_email, send_appraisal_email_preview
from .mail_service import send_appraisal_email as send_appraisal_email_service
from .record_case_sync import sync_record_to_case
from .database_manager import (
    create_outbound_tracking_record,
    create_record_from_values,
    ensure_tracking_record_schema,
    get_record as db_get_record,
    get_record_by_contract_number as db_get_record_by_contract_number,
    log_records_db_path,
    resolve_records_db_path,
    update_record_fields as db_update_record_fields,
    update_record_status as db_update_record_status,
)
from .models import LandCertificateExtraction, LandCertificateMultiExtraction, blank_extraction
from .mail_listener import (
    DEFAULT_LOG_PATH as MAIL_LISTENER_LOG_PATH,
    listener_status_summary,
    read_recent_listener_logs,
    set_listener_enabled,
    write_listener_pid,
)
from .sqlite_store import get_all_organizations


TELEGRAM_WEBHOOK_PATH = "/webhook/telegram"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploads")
DEFAULT_RECORDS_DB = resolve_records_db_path(os.path.join(PROJECT_ROOT, "data", "telegram_records.db"))
DEFAULT_CASES_DB = os.path.join(PROJECT_ROOT, "data", "cases.db")
DEFAULT_EMAIL_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "data", "email_template.txt")
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
PENDING_STATUS = "PENDING"
CONFIRMED_STATUS = "CONFIRMED"
CANCELLED_STATUS = "CANCELLED"
ASK_MISSING_FIELD, CONFIRMING, EDIT_FIELD_SELECT = range(3)
CONFIRM_CALLBACK = "confirm_save"
CANCEL_CALLBACK = "cancel_save"
EDIT_CALLBACK = "edit_info"
SEND_MAIL_CALLBACK_PREFIX = "send_mail"
WEB_AUTOMATION_CALLBACK_PREFIX = "web_entry"
BOTH_AUTOMATION_CALLBACK_PREFIX = "both_entry"
DONE_AUTOMATION_CALLBACK_PREFIX = "done_entry"
HIDDEN_GCN_FIELDS = {"so_thua", "so_to", "dia_chi", "chu_so_huu"}
CUSTOMER_TYPE_LABELS = {
    "individual": "C\u00e1 nh\u00e2n",
    "organization": "T\u1ed5 ch\u1ee9c",
}
REQUIRED_RECORD_FIELDS = [
    ("so_to", "S\u1ed1 t\u1edd b\u1ea3n \u0111\u1ed3"),
    ("so_thua", "S\u1ed1 th\u1eeda \u0111\u1ea5t"),
    ("chu_so_huu", "Ch\u1ee7 s\u1edf h\u1eefu"),
]
TELEGRAM_FORM_FIELDS = [
    ("customer_type", "Lo\u1ea1i kh\u00e1ch h\u00e0ng", "individual"),
    ("contract_number", "S\u1ed1 h\u1ee3p \u0111\u1ed3ng", ""),
    ("asset_type", "Lo\u1ea1i t\u00e0i s\u1ea3n", "B\u0110S \u0111\u1eb7c th\u00f9 kh\u00e1c"),
    ("asset_description", "T\u00e0i s\u1ea3n th\u1ea9m \u0111\u1ecbnh gi\u00e1", ""),
    ("preliminary_status", "S\u01a1 b\u1ed9", "Ch\u01b0a s\u01a1 b\u1ed9"),
    ("expected_finish_date", "Th\u1eddi gian d\u1ef1 ki\u1ebfn ho\u00e0n th\u00e0nh", ""),
    ("valuation_purpose", "M\u1ee5c \u0111\u00edch th\u1ea9m \u0111\u1ecbnh", ""),
    ("source", "Ngu\u1ed3n/\u0111\u1ed1i t\u00e1c", ""),
    ("customer_info", "Th\u00f4ng tin kh\u00e1ch h\u00e0ng", ""),
    ("customer_address", "\u0110\u1ecba ch\u1ec9 kh\u00e1ch h\u00e0ng", ""),
    ("citizen_id", "S\u1ed1 CCCD/CMND", ""),
    ("valuation_fee_number", "Ph\u00ed th\u1ea9m \u0111\u1ecbnh", ""),
    ("advance_payment", "T\u1ea1m \u1ee9ng", "0"),
    ("survey_cost", "Chi ph\u00ed kh\u1ea3o s\u00e1t", "0"),
    ("valuation_staff", "Chuy\u00ean vi\u00ean nghi\u1ec7p v\u1ee5", ""),
    ("personal_note", "Ghi ch\u00fa c\u00e1 nh\u00e2n", ""),
]
TELEGRAM_ORGANIZATION_FIELDS = [
    ("tax_code", "M\u00e3 s\u1ed1 thu\u1ebf", ""),
    ("representative_name", "Ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n", ""),
    ("representative_position", "Ch\u1ee9c v\u1ee5 ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n", ""),
    ("handover_contact_name", "Ng\u01b0\u1eddi nh\u1eadn b\u00e0n giao", ""),
    ("handover_contact_position", "Ch\u1ee9c v\u1ee5 ng\u01b0\u1eddi nh\u1eadn b\u00e0n giao", ""),
    ("handover_contact_phone", "\u0110i\u1ec7n tho\u1ea1i ng\u01b0\u1eddi nh\u1eadn b\u00e0n giao", ""),
    ("authorization_note", "C\u0103n c\u1ee9/gi\u1ea5y \u1ee7y quy\u1ec1n \u0111\u1ea1i di\u1ec7n", ""),
]
TELEGRAM_RECORD_TEXT_COLUMNS = {
    "customer_type",
    "contract_number",
    "asset_type",
    "asset_description",
    "preliminary_status",
    "expected_finish_date",
    "valuation_purpose",
    "source",
    "customer_info",
    "customer_address",
    "citizen_id",
    "valuation_fee_number",
    "advance_payment",
    "survey_cost",
    "valuation_staff",
    "personal_note",
    "tax_code",
    "representative_name",
    "representative_position",
    "authorization_note",
    "handover_contact_name",
    "handover_contact_position",
    "handover_contact_phone",
}
TELEGRAM_SKIPPED_FORM_FIELDS = {"preliminary_status", "expected_finish_date", "survey_cost"}
TELEGRAM_DROPDOWN_FIELDS = {
    "asset_type": "asset_type",
    "valuation_purpose": "valuation_purpose",
    "source": "source",
    "valuation_staff": "valuation_staff",
}
MAX_DROPDOWN_MATCHES = 0


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str
    webhook_url: str
    gemini_api_key: str
    gemini_model: str
    upload_dir: str
    records_db_path: str
    cases_db_path: str = DEFAULT_CASES_DB
    email_template_path: str = DEFAULT_EMAIL_TEMPLATE_PATH
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_to: str = ""
    company_web_url: str = ""
    excel_template_path: str = ""

    @property
    def webhook_endpoint(self) -> str:
        webhook_url = self.webhook_url.rstrip("/")
        if webhook_url.endswith(TELEGRAM_WEBHOOK_PATH):
            return webhook_url
        return f"{webhook_url}{TELEGRAM_WEBHOOK_PATH}"


@dataclass(frozen=True)
class EmailDraft:
    subject: str
    body: str
    to_email: str


def load_telegram_settings() -> TelegramSettings:
    explicit_records_db_path = os.getenv("RECORDS_DB_PATH", "").strip()
    explicit_legacy_records_db_path = os.getenv("TELEGRAM_RECORDS_DB", "").strip()
    load_dotenv(os.path.join(PROJECT_ROOT, "API.env"))
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    upload_dir = os.getenv("TELEGRAM_UPLOAD_DIR", DEFAULT_UPLOAD_DIR).strip() or DEFAULT_UPLOAD_DIR
    records_db_path = resolve_records_db_path(explicit_records_db_path or explicit_legacy_records_db_path or None)
    cases_db_path = os.getenv("TELEGRAM_CASES_DB", os.getenv("SQLITE_DATABASE", DEFAULT_CASES_DB)).strip() or DEFAULT_CASES_DB
    email_template_path = os.getenv("EMAIL_TEMPLATE_PATH", DEFAULT_EMAIL_TEMPLATE_PATH).strip() or DEFAULT_EMAIL_TEMPLATE_PATH
    smtp_port_value = os.getenv("SMTP_PORT", os.getenv("MAIL_PORT", "587")).strip()
    try:
        smtp_port = int(smtp_port_value)
    except ValueError:
        smtp_port = 587
    smtp_username = os.getenv("SMTP_USERNAME", os.getenv("MAIL_USERNAME", "")).strip()
    smtp_password = os.getenv("SMTP_PASSWORD", os.getenv("MAIL_PASSWORD", "")).strip()
    mail_from = os.getenv("MAIL_FROM", "").strip()
    if mail_from and "@" not in mail_from and smtp_username:
        mail_from = formataddr((mail_from, smtp_username))
    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": bot_token,
            "WEBHOOK_URL": webhook_url,
            "GEMINI_API_KEY": gemini_api_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thieu bien moi truong: {', '.join(missing)}")
    return TelegramSettings(
        bot_token=bot_token,
        webhook_url=webhook_url,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        upload_dir=upload_dir,
        records_db_path=records_db_path,
        cases_db_path=cases_db_path,
        email_template_path=email_template_path,
        smtp_host=os.getenv("SMTP_HOST", os.getenv("MAIL_SERVER", "")).strip(),
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        mail_from=mail_from,
        mail_to=os.getenv("MAIL_TO", "").strip(),
        company_web_url=os.getenv("COMPANY_WEB_URL", "").strip(),
        excel_template_path=os.getenv("EXCEL_TEMPLATE_PATH", "").strip(),
    )


def _safe_file_name(file_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", file_name).strip("._")
    return cleaned or "telegram_file"


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    # Replace common punctuation with spaces
    without_punct = re.sub(r"[,\.;\-_\(\)\[\]\{\}]", " ", without_marks)
    return re.sub(r"\s+", " ", without_punct.lower()).strip()


def _score_dropdown_option(query: str, option: str) -> int:
    normalized_query = _normalize_search_text(query)
    normalized_option = _normalize_search_text(option)
    if not normalized_query:
        return 0
    tokens = [token for token in normalized_query.split(" ") if token]
    score = 0
    if normalized_query == normalized_option:
        score += 100
    if normalized_query in normalized_option:
        score += 60
    for token in tokens:
        if token in normalized_option:
            score += 20
    if tokens and all(token in normalized_option for token in tokens):
        score += 40
    return score


def search_dropdown_options(query: str, options: list[str], *, limit: int = MAX_DROPDOWN_MATCHES) -> list[str]:
    scored = [
        (score, index, option)
        for index, option in enumerate(options)
        if (score := _score_dropdown_option(query, option)) > 0
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    if limit > 0:
        scored = scored[:limit]
    return [option for _score, _index, option in scored]


def _unique_upload_path(upload_dir: str, file_name: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = _safe_file_name(file_name)
    stem, suffix = os.path.splitext(safe_name)
    return os.path.join(upload_dir, f"{uuid4().hex}_{stem}{suffix}")


async def init_records_db(db_path: str) -> None:
    await ensure_tracking_record_schema(db_path)


def _first_extracted_asset(
    extraction: LandCertificateExtraction | LandCertificateMultiExtraction,
) -> LandCertificateExtraction:
    if isinstance(extraction, LandCertificateExtraction):
        return extraction
    assets = getattr(extraction, "assets", [])
    return assets[0] if assets else blank_extraction()


async def save_record(
    db_path: str,
    file_path: str,
    extraction: LandCertificateExtraction | LandCertificateMultiExtraction,
) -> int:
    form_values = extraction_to_record_values(extraction)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        cursor_defaults = await db.execute(
            """
            SELECT preliminary_status, expected_finish_date, survey_cost
            FROM records
            ORDER BY id DESC
            LIMIT 1
            """
        )
        previous_defaults = await cursor_defaults.fetchone()
        if previous_defaults is not None:
            for index, field in enumerate(["preliminary_status", "expected_finish_date", "survey_cost"]):
                previous_value = str(previous_defaults[index] or "").strip()
                if previous_value:
                    form_values[field] = previous_value
    return await create_record_from_values(db_path, form_values, file_path=file_path, status=PENDING_STATUS)


async def update_record_fields(db_path: str, record_id: int, values: dict[str, str]) -> None:
    await db_update_record_fields(db_path, record_id, values)


async def update_record_status(db_path: str, record_id: int, status: str) -> None:
    await db_update_record_status(db_path, record_id, status)


async def get_record(db_path: str, record_id: int) -> dict[str, str]:
    return await db_get_record(db_path, record_id)


async def get_record_by_contract_number(db_path: str, contract_query: str) -> dict[str, str] | None:
    return await db_get_record_by_contract_number(db_path, contract_query)


async def get_case_by_contract_number(db_path: str, contract_query: str) -> dict[str, str] | None:
    query = (contract_query or "").strip()
    if not query or not os.path.exists(db_path):
        return None
    short_query = short_contract_number(query)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        table_cursor = await db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'cases'")
        if await table_cursor.fetchone() is None:
            return None
        cursor = await db.execute(
            """
            SELECT *
            FROM cases
            WHERE TRIM(contract_number) <> ''
            ORDER BY id DESC
            """
        )
        rows = await cursor.fetchall()

    for row in rows:
        record = {key: str(row[key] or "") for key in row.keys()}
        contract_number = record.get("contract_number", "")
        if contract_number == query or short_contract_number(contract_number) == short_query:
            return record
    return None


async def find_record_for_contract(settings: TelegramSettings, contract_query: str) -> tuple[dict[str, str] | None, str]:
    record = await get_record_by_contract_number(settings.records_db_path, contract_query)
    if record is not None:
        return record, "telegram"
    case = await get_case_by_contract_number(settings.cases_db_path, contract_query)
    if case is not None:
        return case, "cases"
    return None, ""


def _default_email_template() -> str:
    return (
        "Kinh gui Anh/Chi,\n\n"
        "He thong da xac nhan ho so GCN #{id} voi thong tin sau:\n"
        "- So thua: {so_thua}\n"
        "- So to ban do: {so_to}\n"
        "- Dia chi thua dat: {dia_chi}\n"
        "- Chu so huu: {chu_so_huu}\n"
        "- Trang thai: {status}\n\n"
        "Vui long kiem tra va thuc hien cac buoc tiep theo.\n"
    )


def _load_email_template(template_path: str) -> str:
    if template_path and os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as template_file:
            return template_file.read()
    return _default_email_template()


async def draft_email(
    record_id: int,
    db_path: str = DEFAULT_RECORDS_DB,
    *,
    template_path: str = DEFAULT_EMAIL_TEMPLATE_PATH,
    to_email: str = "",
) -> EmailDraft:
    record = await get_record(db_path, record_id)
    template = _load_email_template(template_path)
    subject = f"Ho so GCN #{record_id} - {record.get('chu_so_huu', '')}".strip()
    body = template.format(**record)
    return EmailDraft(subject=subject, body=body, to_email=to_email)


def format_email_draft_message(draft: EmailDraft) -> str:
    recipient = draft.to_email or "Chua cau hinh MAIL_TO"
    return "\n".join(
        [
            "Ban thao email:",
            f"To: {recipient}",
            f"Subject: {draft.subject}",
            "",
            draft.body,
        ]
    )


def automation_keyboard(record_id: int, mail_done: bool = False, web_done: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not mail_done and not web_done:
        buttons.append([InlineKeyboardButton("📧 Gửi Mail (Hành chính)", callback_data=f"{SEND_MAIL_CALLBACK_PREFIX}:{record_id}")])
        buttons.append([InlineKeyboardButton("🌐 Nhập Web (Nội bộ)", callback_data=f"{WEB_AUTOMATION_CALLBACK_PREFIX}:{record_id}")])
        buttons.append([InlineKeyboardButton("⚡ Thực hiện CẢ HAI (Mail + Web)", callback_data=f"{BOTH_AUTOMATION_CALLBACK_PREFIX}:{record_id}")])
    elif not mail_done:
        buttons.append([InlineKeyboardButton("📧 Gửi Mail (Hành chính)", callback_data=f"{SEND_MAIL_CALLBACK_PREFIX}:{record_id}")])
        buttons.append([InlineKeyboardButton("✅ Hoàn tất", callback_data=f"{DONE_AUTOMATION_CALLBACK_PREFIX}:{record_id}")])
    elif not web_done:
        buttons.append([InlineKeyboardButton("🌐 Nhập Web (Nội bộ)", callback_data=f"{WEB_AUTOMATION_CALLBACK_PREFIX}:{record_id}")])
        buttons.append([InlineKeyboardButton("✅ Hoàn tất", callback_data=f"{DONE_AUTOMATION_CALLBACK_PREFIX}:{record_id}")])
    else:
        buttons.append([InlineKeyboardButton("✅ Đã hoàn tất", callback_data=f"{DONE_AUTOMATION_CALLBACK_PREFIX}:{record_id}")])
        
    return InlineKeyboardMarkup(buttons)


def _send_email_sync(settings: TelegramSettings, draft: EmailDraft) -> None:
    mail_from = settings.mail_from or settings.smtp_username
    mail_to = draft.to_email or settings.mail_to
    missing = [
        name
        for name, value in {
            "SMTP_HOST": settings.smtp_host,
            "MAIL_FROM/SMTP_USERNAME": mail_from,
            "MAIL_TO": mail_to,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thieu cau hinh gui mail: {', '.join(missing)}")

    message = EmailMessage()
    message["From"] = mail_from
    message["To"] = mail_to
    message["Subject"] = draft.subject
    message.set_content(draft.body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_email(settings: TelegramSettings, draft: EmailDraft) -> None:
    await to_thread(_send_email_sync, settings, draft)


def extraction_to_record_values(
    extraction: LandCertificateExtraction | LandCertificateMultiExtraction,
) -> dict[str, str]:
    asset = _first_extracted_asset(extraction)
    so_thua = asset.so_thua_dat.value.strip()
    so_to = asset.so_to_ban_do.value.strip()
    dia_chi = asset.dia_chi_thua_dat.value.strip()
    chu_so_huu = asset.ten_chu_so_huu_cuoi_cung.value.strip()
    owner_address = asset.dia_chi_chu_so_huu_cuoi_cung.value.strip()
    citizen_id = asset.so_cccd_chu_so_huu_cuoi_cung.value.strip()

    asset_description_parts = []
    if so_thua:
        asset_description_parts.append(f"Thửa đất số {so_thua}")
    if so_to:
        asset_description_parts.append(f"tờ bản đồ số {so_to}")
    asset_desc = ", ".join(asset_description_parts)
    if dia_chi:
        asset_desc = (
            f"{asset_desc}; tại địa chỉ {dia_chi}."
            if asset_desc
            else f"Thửa đất tại địa chỉ {dia_chi}."
        )

    values = _default_form_values()
    values.update({
        "so_thua": so_thua,
        "so_to": so_to,
        "dia_chi": dia_chi,
        "chu_so_huu": chu_so_huu,
        "customer_type": "individual",
        "asset_type": "BĐS đặc thù khác",
        "asset_description": asset_desc,
        "preliminary_status": "Chưa sơ bộ",
        "customer_info": chu_so_huu,
        "customer_address": owner_address,
        "citizen_id": citizen_id,
        "advance_payment": "0",
        "survey_cost": "0",
    })
    return values


def missing_required_fields(values: dict[str, str]) -> list[tuple[str, str]]:
    return [(field, label) for field, label in REQUIRED_RECORD_FIELDS if not values.get(field, "").strip()]


def manual_missing_required_fields(values: dict[str, str]) -> list[tuple[str, str]]:
    del values
    return []


def build_form_field_queue(values: dict[str, str]) -> list[tuple[str, str]]:
    queue = [
        (field, label)
        for field, label, _default in TELEGRAM_FORM_FIELDS
        if field not in TELEGRAM_SKIPPED_FORM_FIELDS
    ]
    if values.get("customer_type") == "organization":
        queue.extend((field, label) for field, label, _default in TELEGRAM_ORGANIZATION_FIELDS)
    return queue


def editable_record_fields(values: dict[str, str]) -> list[tuple[str, str]]:
    fields = [
        ("so_thua", "S\u1ed1 th\u1eeda"),
        ("so_to", "S\u1ed1 t\u1edd b\u1ea3n \u0111\u1ed3"),
        ("dia_chi", "\u0110\u1ecba ch\u1ec9 th\u1eeda \u0111\u1ea5t"),
        ("chu_so_huu", "Ch\u1ee7 s\u1edf h\u1eefu"),
    ]
    fields = [item for item in fields if item[0] not in HIDDEN_GCN_FIELDS]
    fields.extend(
        (field, label)
        for field, label, _default in TELEGRAM_FORM_FIELDS
        if field not in TELEGRAM_SKIPPED_FORM_FIELDS
    )
    if values.get("customer_type") == "organization":
        fields.extend((field, label) for field, label, _default in TELEGRAM_ORGANIZATION_FIELDS)
    return fields


def format_editable_field_list(values: dict[str, str]) -> str:
    lines = ["Anh mu\u1ed1n s\u1eeda m\u1ee5c n\u00e0o? Tr\u1ea3 l\u1eddi s\u1ed1 th\u1ee9 t\u1ef1 c\u1ee7a m\u1ee5c c\u1ea7n s\u1eeda:"]
    for index, (field, label) in enumerate(editable_record_fields(values), start=1):
        value = _display_record_value(field, values.get(field) or "")
        lines.append(f"{index}. {label}: {value}")
    return "\n".join(lines)


def _display_record_value(field: str, value: str) -> str:
    if field == "customer_type":
        return CUSTOMER_TYPE_LABELS.get(value, value or "C\u00e1 nh\u00e2n")
    if field == "contract_number":
        return short_contract_number(value, fallback="Ch\u01b0a c\u00f3")
    return value or "Ch\u01b0a c\u00f3"


def _default_form_values() -> dict[str, str]:
    values = {field: default for field, _label, default in TELEGRAM_FORM_FIELDS}
    values.update({field: default for field, _label, default in TELEGRAM_ORGANIZATION_FIELDS})
    return values


def _normalize_customer_type(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"organization", "to chuc", "t\u1ed5 ch\u1ee9c", "doanh nghiep", "doanh nghi\u1ec7p", "cong ty", "c\u00f4ng ty"}:
        return "organization"
    if lowered in {"individual", "ca nhan", "c\u00e1 nh\u00e2n"}:
        return "individual"
    return value.strip()


def _find_first_match(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" ,;.-")
    return ""


def sync_hidden_gcn_fields_from_form(values: dict[str, str]) -> dict[str, str]:
    synced = dict(values)
    asset_description = str(synced.get("asset_description") or "")
    if not str(synced.get("chu_so_huu") or "").strip():
        synced["chu_so_huu"] = str(synced.get("customer_info") or "").strip()
    if not str(synced.get("so_thua") or "").strip():
        synced["so_thua"] = _find_first_match(
            [
                r"thửa\s*đất\s*số\s*([^,;.\n]+)",
                r"thua\s*dat\s*so\s*([^,;.\n]+)",
            ],
            asset_description,
        )
    if not str(synced.get("so_to") or "").strip():
        synced["so_to"] = _find_first_match(
            [
                r"tờ\s*bản\s*đồ\s*số\s*([^,;.\n]+)",
                r"to\s*ban\s*do\s*so\s*([^,;.\n]+)",
            ],
            asset_description,
        )
    if not str(synced.get("dia_chi") or "").strip():
        address = _find_first_match(
            [
                r"(?:tại\s+)?địa\s*chỉ\s+(.+?)(?:\.|$)",
                r"(?:tai\s+)?dia\s*chi\s+(.+?)(?:\.|$)",
            ],
            asset_description,
        )
        synced["dia_chi"] = address or str(synced.get("customer_address") or "").strip()
    return synced


def _field_label(field_name: str) -> str:
    for field, label, _default in [*TELEGRAM_FORM_FIELDS, *TELEGRAM_ORGANIZATION_FIELDS]:
        if field == field_name:
            return label
    for field, label in REQUIRED_RECORD_FIELDS:
        if field == field_name:
            return label
    return field_name


def format_extraction_response(
    record_id: int,
    extraction: LandCertificateExtraction | LandCertificateMultiExtraction,
) -> str:
    asset = _first_extracted_asset(extraction)
    lines = [f"Da quet GCN va luu ban ghi #{record_id}.", ""]
    lines.append(f"So thua: {asset.so_thua_dat.value or 'Chua doc duoc'}")
    lines.append(f"So to ban do: {asset.so_to_ban_do.value or 'Chua doc duoc'}")
    lines.append(f"Dia chi thua dat: {asset.dia_chi_thua_dat.value or 'Chua doc duoc'}")
    lines.append(f"Chu so huu: {asset.ten_chu_so_huu_cuoi_cung.value or 'Chua doc duoc'}")
    lines.append("")
    lines.append(f"Trang thai: {PENDING_STATUS}")
    return "\n".join(lines)


def format_record_summary(record_id: int, values: dict[str, str]) -> str:
    lines = [
        f"Thông tin hồ sơ #{record_id}:",
        "",
    ]
    for index, (field, label) in enumerate(editable_record_fields(values), start=1):
        value = _display_record_value(field, values.get(field) or "")
        if "\n" in value:
            lines.append(f"{index}. {label}:")
            for line in value.split("\n"):
                if line.strip():
                    lines.append(f"  🔹 {line.strip()}")
        else:
            lines.append(f"{index}. {label}: {value}")
    lines.append(f"Trạng thái: {PENDING_STATUS}")
    return "\n".join(lines)


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("S\u1eeda th\u00f4ng tin", callback_data=EDIT_CALLBACK),
            ],
            [
                InlineKeyboardButton("X\u00e1c nh\u1eadn l\u01b0u", callback_data=CONFIRM_CALLBACK),
                InlineKeyboardButton("H\u1ee7y b\u1ecf", callback_data=CANCEL_CALLBACK),
            ]
        ]
    )


def _set_conversation_record(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    record_id: int,
    db_path: str,
    values: dict[str, str],
) -> None:
    context.user_data["pending_record"] = {
        "record_id": record_id,
        "db_path": db_path,
        "values": values,
        "form_fields": build_form_field_queue(values),
        "missing_fields": missing_required_fields(values),
    }


def _get_conversation_record(context: ContextTypes.DEFAULT_TYPE) -> dict[str, object] | None:
    record = context.user_data.get("pending_record")
    return record if isinstance(record, dict) else None


async def _ask_next_missing_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is None or update.effective_message is None:
        return ConversationHandler.END
    form_fields = record.get("form_fields")
    if isinstance(form_fields, list) and form_fields:
        field, label = form_fields[0]
        values = dict(record.get("values") or {})
        current_value = values.get(str(field), "")
        display_current_value = _display_record_value(str(field), current_value) if current_value else ""
        hint = (
            f"Giá trị hiện tại: {display_current_value}\n"
            "Nhập giá trị mới, hoặc nhập '.' để giữ nguyên/bỏ qua."
            if current_value
            else "Nhập giá trị, hoặc nhập '.' để bỏ qua."
        )
        if field == "customer_type":
            hint += "\nG\u1ee3i \u00fd: nh\u1eadp 'c\u00e1 nh\u00e2n' ho\u1eb7c 't\u1ed5 ch\u1ee9c'."
        if str(field) in TELEGRAM_DROPDOWN_FIELDS:
            hint += "\n\u0110\u00e2y l\u00e0 tr\u01b0\u1eddng c\u00f3 danh s\u00e1ch ch\u1ecdn. Nh\u1eadp t\u1eeb kh\u00f3a, bot s\u1ebd t\u00ecm g\u1ee3i \u00fd ph\u00f9 h\u1ee3p."
        await update.effective_message.reply_text(f"{label}:\n{hint}")
        return ASK_MISSING_FIELD
    missing_fields = record.get("missing_fields")
    if not isinstance(missing_fields, list) or not missing_fields:
        return await _show_confirmation(update, context)
    _field, label = missing_fields[0]
    await update.effective_message.reply_text(f"Thi\u1ebfu {label}. Vui l\u00f2ng nh\u1eadp b\u1ed5 sung:")
    return ASK_MISSING_FIELD


async def _show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is None or update.effective_message is None:
        return ConversationHandler.END
    record_id = int(record["record_id"])
    values = sync_hidden_gcn_fields_from_form(dict(record["values"]))
    record["values"] = values
    await update_record_fields(
        str(record["db_path"]),
        record_id,
        {field: values.get(field, "") for field in HIDDEN_GCN_FIELDS},
    )
    await update.effective_message.reply_text(
        format_record_summary(record_id, values),
        reply_markup=confirmation_keyboard(),
    )
    return CONFIRMING


async def _download_telegram_file(file_ref: PhotoSize | Document, destination_path: str) -> None:
    telegram_file = await file_ref.get_file()
    await telegram_file.download_to_drive(custom_path=destination_path)


async def process_land_certificate_file(
    *,
    file_ref: PhotoSize | Document,
    file_name: str,
    settings: TelegramSettings,
) -> tuple[int, str, LandCertificateMultiExtraction]:
    upload_path = _unique_upload_path(settings.upload_dir, file_name)
    await _download_telegram_file(file_ref, upload_path)
    extraction = await to_thread(
        extract_land_certificate_with_gemini,
        upload_path,
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )

    record_id = await save_record(settings.records_db_path, upload_path, extraction)
    return record_id, upload_path, extraction


def _settings_from_context(context: ContextTypes.DEFAULT_TYPE) -> TelegramSettings:
    settings = context.application.bot_data.get("settings")
    if not isinstance(settings, TelegramSettings):
        raise RuntimeError("Telegram settings chua duoc khoi tao.")
    return settings


def _dropdown_options_from_context(context: ContextTypes.DEFAULT_TYPE, field_name: str) -> list[str]:
    dropdown_options = context.application.bot_data.get("excel_dropdown_options", {})
    if not isinstance(dropdown_options, dict):
        return []
    values = dropdown_options.get(TELEGRAM_DROPDOWN_FIELDS.get(field_name, field_name), [])
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _save_env_value(path: str | os.PathLike[str], key: str, value: str) -> None:
    env_path = Path(path)
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated = False
    output_lines: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            output_lines.append(f"{key}={value}")
            updated = True
        else:
            output_lines.append(line)
    if not updated:
        output_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")


async def chat_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None or update.effective_chat is None:
        return
    chat_id = str(update.effective_chat.id)
    _save_env_value(os.path.join(PROJECT_ROOT, "API.env"), "TELEGRAM_CHAT_ID", chat_id)
    await update.effective_message.reply_text(f"\u0110\u00e3 l\u01b0u TELEGRAM_CHAT_ID={chat_id} v\u00e0o API.env.")


def _listener_updated_by(update: Update) -> str:
    user = update.effective_user
    if user is None:
        return "telegram"
    label = user.username or user.full_name or str(user.id)
    return f"telegram:{label}"


def _start_mail_listener_background() -> int:
    status = listener_status_summary()
    if status.get("running") and status.get("pid"):
        return int(status["pid"])

    log_dir = Path(PROJECT_ROOT) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "mail_listener_stdout.log"
    stderr_path = log_dir / "mail_listener_stderr.log"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with stdout_path.open("a", encoding="utf-8") as stdout, stderr_path.open("a", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            [sys.executable, "-m", "src.mail_listener"],
            cwd=PROJECT_ROOT,
            stdout=stdout,
            stderr=stderr,
            creationflags=creationflags,
        )
    write_listener_pid(process.pid)
    return process.pid


def _format_listener_status() -> str:
    status = listener_status_summary()
    enabled_text = "B\u1eadt" if status.get("enabled") else "T\u1eaft"
    running_text = "\u0110ang ch\u1ea1y" if status.get("running") else "Ch\u01b0a ch\u1ea1y"
    pid_text = status.get("pid") or "Kh\u00f4ng c\u00f3"
    return (
        "Tr\u1ea1ng th\u00e1i Mail Listener:\n"
        f"- Theo d\u00f5i Gmail: {enabled_text}\n"
        f"- Ti\u1ebfn tr\u00ecnh n\u1ec1n: {running_text}\n"
        f"- PID: {pid_text}\n"
        f"- Log: {MAIL_LISTENER_LOG_PATH}"
    )


def _format_listener_logs(limit: int = 10) -> str:
    logs = read_recent_listener_logs(limit)
    if not logs:
        return "Ch\u01b0a c\u00f3 log Mail Listener."
    lines = ["10 d\u00f2ng log Mail Listener g\u1ea7n nh\u1ea5t:"]
    for item in logs[-limit:]:
        event = str(item.get("event", "unknown"))
        time_text = str(item.get("time", ""))
        subject = str(item.get("subject", "")).strip()
        reason = str(item.get("reason", "")).strip()
        record_id = str(item.get("record_id", "")).strip()
        score = item.get("score", "")
        detail_parts = []
        if record_id:
            detail_parts.append(f"HS #{record_id}")
        if score not in ("", None):
            detail_parts.append(f"score {score}")
        if reason:
            detail_parts.append(reason)
        if subject:
            detail_parts.append(subject[:90])
        detail = " | ".join(detail_parts)
        lines.append(f"- {time_text} [{event}] {detail}".rstrip())
    return "\n".join(lines)


async def listener_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    try:
        set_listener_enabled(True, updated_by=_listener_updated_by(update))
        pid = _start_mail_listener_background()
        await update.effective_message.reply_text(
            f"\u0110\u00e3 b\u1eadt Mail Listener v\u00e0 \u0111\u1ea3m b\u1ea3o ti\u1ebfn tr\u00ecnh n\u1ec1n \u0111ang ch\u1ea1y. PID: {pid}\n\n{_format_listener_status()}"
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"B\u1eadt Mail Listener th\u1ea5t b\u1ea1i: {exc}")


async def listener_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    try:
        set_listener_enabled(False, updated_by=_listener_updated_by(update))
        await update.effective_message.reply_text(
            "\u0110\u00e3 t\u1eaft theo d\u00f5i Gmail. Ti\u1ebfn tr\u00ecnh n\u1ec1n v\u1eabn c\u00f3 th\u1ec3 c\u00f2n ch\u1ea1y nh\u01b0ng s\u1ebd b\u1ecf qua c\u00e1c v\u00f2ng qu\u00e9t m\u1edbi.\n\n"
            f"{_format_listener_status()}"
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"T\u1eaft Mail Listener th\u1ea5t b\u1ea1i: {exc}")


async def listener_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(_format_listener_status())


async def listener_log_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(_format_listener_logs(10))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "Xin chao. Bot da san sang nhan hinh anh/PDF de quet GCN. "
        "Neu muon nhap ho so thu cong khong can quet GCN, hay go /nhap. "
        "Neu muon gui mail yeu cau dinh gia theo so hop dong, hay go /gui_mail N04-1051. "
        "Neu muon tra cuu ho so hoac nhap web/gui mail, hay go /tra_cuu N04-1051. "
        "Neu can luu chat id de listener thong bao, hay go /chat_id. "
        "Quan ly listener: /listener_on, /listener_off, /listener_status, /listener_log."
    )


async def send_mail_by_contract_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    contract_query = " ".join(context.args or []).strip()
    if not contract_query:
        await update.effective_message.reply_text(
            "Vui lòng nhập số hợp đồng sau lệnh. Ví dụ: /gui_mail N04-1051"
        )
        return

    settings = _settings_from_context(context)
    short_query = short_contract_number(contract_query)
    await update.effective_message.reply_text(f"Đang tìm hồ sơ {short_query} và gửi mail yêu cầu định giá...")
    try:
        record, record_source = await find_record_for_contract(settings, contract_query)
        if record is None:
            await update.effective_message.reply_text(f"Không tìm thấy hồ sơ có số hợp đồng {short_query}.")
            return
        mail_payload = {**record, "to_email": settings.mail_to}
        if record_source == "cases":
            tracking_id = await create_outbound_tracking_record(settings.records_db_path, record, file_path="telegram_case")
            mail_payload.pop("id", None)
            mail_payload["record_id"] = tracking_id
            mail_payload["records_db_path"] = settings.records_db_path
        await send_appraisal_email_service(mail_payload)
        contract_label = short_contract_number(record.get("contract_number"), fallback=short_query)
        source_label = "quản lý hồ sơ" if record_source == "cases" else "Telegram"
        await update.effective_message.reply_text(f"Đã gửi mail thành công cho hồ sơ {contract_label} từ {source_label}.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Gửi mail thất bại cho hồ sơ {short_query}: {exc}")


async def search_case_by_contract_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    contract_query = " ".join(context.args or []).strip()
    if not contract_query:
        await update.effective_message.reply_text(
            "Vui lòng nhập số hợp đồng sau lệnh. Ví dụ: /tra_cuu N04-1051"
        )
        return

    settings = _settings_from_context(context)
    short_query = short_contract_number(contract_query)
    await update.effective_message.reply_text(f"Đang tìm hồ sơ {short_query}...")
    try:
        record, record_source = await find_record_for_contract(settings, contract_query)
        if record is None:
            await update.effective_message.reply_text(f"Không tìm thấy hồ sơ có số hợp đồng {short_query}.")
            return
            
        if record_source == "cases":
            tracking_id = await create_outbound_tracking_record(settings.records_db_path, record, file_path="telegram_case")
            record_id = tracking_id
        else:
            record_id = int(record.get("id", 0))

        summary = format_record_summary(record_id, record)
        await update.effective_message.reply_text(
            f"Tìm thấy hồ sơ {short_query}:\n\n{summary}",
            reply_markup=automation_keyboard(record_id)
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Lỗi khi tra cứu hồ sơ {short_query}: {exc}")


async def start_manual_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    try:
        settings = _settings_from_context(context)
        extraction = blank_extraction()
        record_id = await save_record(settings.records_db_path, "manual_entry", extraction)
        values = await get_record(settings.records_db_path, record_id)
    except Exception as exc:
        await update.effective_message.reply_text(f"Khong tao duoc ho so thu cong: {exc}")
        return ConversationHandler.END

    _set_conversation_record(
        context,
        record_id=record_id,
        db_path=settings.records_db_path,
        values=values,
    )
    record = _get_conversation_record(context)
    if record is not None:
        record["manual_entry"] = True
        record["form_fields"] = build_form_field_queue(values)
        record["missing_fields"] = manual_missing_required_fields(values)
        record.pop("pending_dropdown", None)

    await update.effective_message.reply_text(
        f"Da tao ho so nhap thu cong #{record_id}. Bot se hoi tung thong tin can dien."
    )
    return await _ask_next_missing_field(update, context)


async def request_manual_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    template = (
        "Anh/chị hãy copy bảng dưới đây, điền thông tin và gửi lại cho bot:\n\n"
        "1. Loại khách hàng: Cá nhân\n"
        "2. Số hợp đồng: Chưa có\n"
        "3. Loại tài sản: BĐS đặc thù khác\n"
        "4. Tài sản thẩm định giá: \n"
        "5. Mục đích thẩm định: Làm cơ sở tham khảo để thế chấp vay vốn tại Vietcombank\n"
        "6. Nguồn/đối tác: \n"
        "7. Thông tin khách hàng: \n"
        "8. Địa chỉ khách hàng: \n"
        "9. Số CCCD/CMND: Chưa có\n"
        "10. Phí thẩm định: 3000000\n"
        "11. Tạm ứng: 0\n"
        "12. Chuyên viên nghiệp vụ: Thampt2\n"
        "13. Ghi chú cá nhân: "
    )
    await update.effective_message.reply_text(template)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    text = update.effective_message.text or ""
    text_lower = text.lower()

    if "1. loại khách hàng:" in text_lower and "4. tài sản thẩm định giá:" in text_lower:
        await process_manual_template_submission(update, context, text)
        return

    # Nhận diện lệnh tra cứu / tìm kiếm
    match_search = re.search(r'(?:tra c[ứu]{1,2}u|tìm kiếm|tìm|kiểm tra|check|hồ sơ)\s+([a-z0-9\-]+)', text_lower)
    if match_search:
        context.args = [match_search.group(1)]
        await search_case_by_contract_command(update, context)
        return

    # Nhận diện lệnh gửi mail
    match_mail = re.search(r'(?:gửi mail|gửi|mail)\s+([a-z0-9\-]+)', text_lower)
    if match_mail:
        context.args = [match_mail.group(1)]
        await send_mail_by_contract_command(update, context)
        return

    # Gợi ý nếu gõ các từ khoá khác
    if text_lower in ["nhập", "nhập hồ sơ", "tạo hồ sơ", "new"]:
        await update.effective_message.reply_text("Để nhập hồ sơ thủ công, bạn có thể gửi ảnh sổ đỏ, gõ lệnh /nhap, hoặc /nhapthucong nhé.")
        return

    await update.effective_message.reply_text(f"Gợi ý: Bạn có thể nhắn tự nhiên như 'tìm N04-1027', 'tra cứu N04-1027', hoặc 'gửi mail N04-1027'.")


async def process_manual_template_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    settings = _settings_from_context(context)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    values = {}
    
    field_map = {
        "1. loại khách hàng:": "customer_type",
        "2. số hợp đồng:": "contract_number",
        "3. loại tài sản:": "asset_type",
        "4. tài sản thẩm định giá:": "asset_description",
        "5. mục đích thẩm định:": "valuation_purpose",
        "6. nguồn/đối tác:": "source",
        "7. thông tin khách hàng:": "customer_info",
        "8. địa chỉ khách hàng:": "customer_address",
        "9. số cccd/cmnd:": "citizen_id",
        "10. phí thẩm định:": "valuation_fee_number",
        "11. tạm ứng:": "advance_payment",
        "12. chuyên viên nghiệp vụ:": "valuation_staff",
        "13. ghi chú cá nhân:": "personal_note",
    }
    
    for line in lines:
        lower_line = line.lower()
        for prefix, db_field in field_map.items():
            if lower_line.startswith(prefix):
                values[db_field] = line[len(prefix):].strip()
                break
                
    if values.get("customer_type", "").lower() == "cá nhân":
        values["customer_type"] = "individual"
    elif values.get("customer_type", "").lower() == "tổ chức":
        values["customer_type"] = "organization"
        
    asset_desc = values.get("asset_description", "").strip()
    if asset_desc:
        import re
        m = re.match(r"^(\d+)\s*,\s*(\d+)\s*,\s*(?:địa\s+chỉ\s+)?(.+)$", asset_desc, re.IGNORECASE)
        if m:
            values["asset_description"] = f"Thửa đất số {m.group(1)}, tờ bản đồ số {m.group(2)}, tại địa chỉ {m.group(3)}"
            
    for field in TELEGRAM_DROPDOWN_FIELDS:
        val = values.get(field, "").strip()
        if val:
            options = _dropdown_options_from_context(context, field)
            if options:
                if field == "source" and "," in val:
                    org_part, person_part = [p.strip() for p in val.split(",", 1)]
                    from .sqlite_store import get_all_organizations
                    orgs = get_all_organizations(settings.cases_db_path)
                    
                    matched_org_name = org_part
                    for org in orgs:
                        abbrev = org.get("abbreviation") or ""
                        if abbrev.strip().lower() == org_part.lower() and abbrev.strip():
                            matched_org_name = org.get("name") or org_part
                            break
                            
                    org_part_norm = _normalize_search_text(org_part).replace(",", "")
                    matched_org_norm = _normalize_search_text(matched_org_name).replace(",", "")
                    
                    filtered_options = []
                    for opt in options:
                        opt_norm = _normalize_search_text(opt)
                        if org_part_norm in opt_norm or matched_org_norm in opt_norm:
                            filtered_options.append(opt)
                            
                    search_pool = filtered_options if filtered_options else options
                    val_to_search = person_part.replace(",", "")
                    matches = search_dropdown_options(val_to_search, search_pool)
                    if matches:
                        values[field] = matches[0]
                else:
                    # Also replace commas for standard search so it doesn't break token matching
                    val_clean = val.replace(",", " ")
                    matches = search_dropdown_options(val_clean, options)
                    if matches:
                        values[field] = matches[0]

    if values.get("customer_type") == "organization":
        customer_info = values.get("customer_info", "").strip()
        if customer_info:
            from .sqlite_store import get_all_organizations
            orgs = get_all_organizations(settings.cases_db_path)
            for org in orgs:
                abbrev = org.get("abbreviation") or ""
                if abbrev.strip().lower() == customer_info.lower() and abbrev.strip():
                    values["customer_info"] = org.get("name") or ""
                    if not values.get("tax_code"):
                        values["tax_code"] = org.get("tax_code") or ""
                    if not values.get("customer_address"):
                        values["customer_address"] = org.get("address") or ""
                    if not values.get("representative_name"):
                        values["representative_name"] = org.get("representative") or ""
                    if not values.get("representative_position"):
                        values["representative_position"] = org.get("position") or ""
                    break

    # Đồng bộ các trường bị ẩn
    synced_values = sync_hidden_gcn_fields_from_form(values)
    values.update(synced_values)
        
    try:
        from .database_manager import create_record_from_values
        record_id = await create_record_from_values(settings.records_db_path, values, file_path="manual_template")
        await db_update_record_status(settings.records_db_path, record_id, CONFIRMED_STATUS)
        
        record = await db_get_record(settings.records_db_path, record_id)
        summary = format_record_summary(record_id, record)
        await update.effective_message.reply_text(
            f"Đã tạo hồ sơ thành công từ mẫu nhập tay:\n\n{summary}",
            reply_markup=automation_keyboard(record_id)
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Lỗi khi lưu hồ sơ: {exc}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None or not update.effective_message.photo:
        return ConversationHandler.END
    await update.effective_message.reply_text("Đã nhận hình ảnh, đang quét GCN bằng AI...")
    try:
        settings = _settings_from_context(context)
        photo = update.effective_message.photo[-1]
        record_id, _upload_path, extraction = await process_land_certificate_file(
            file_ref=photo,
            file_name=f"{photo.file_unique_id}.jpg",
            settings=settings,
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Quét GCN thất bại: {exc}")
        return ConversationHandler.END

    values = extraction_to_record_values(extraction)
    _set_conversation_record(
        context,
        record_id=record_id,
        db_path=settings.records_db_path,
        values=values,
    )
    await update.effective_message.reply_text(format_extraction_response(record_id, extraction))
    return await _ask_next_missing_field(update, context)


async def handle_pdf_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    document = update.effective_message.document
    if document is None:
        await update.effective_message.reply_text("Khong tim thay tep PDF trong tin nhan.")
        return ConversationHandler.END
    file_name = document.file_name or f"{document.file_unique_id}.pdf"
    await update.effective_message.reply_text(f"Đã nhận {file_name}, đang quét GCN bằng AI...")
    try:
        settings = _settings_from_context(context)
        record_id, _upload_path, extraction = await process_land_certificate_file(
            file_ref=document,
            file_name=file_name,
            settings=settings,
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Quét GCN thất bại: {exc}")
        return ConversationHandler.END

    values = extraction_to_record_values(extraction)
    _set_conversation_record(
        context,
        record_id=record_id,
        db_path=settings.records_db_path,
        values=values,
    )
    await update.effective_message.reply_text(format_extraction_response(record_id, extraction))
    return await _ask_next_missing_field(update, context)


async def handle_missing_field_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is None or update.effective_message is None:
        return ConversationHandler.END
    text = (update.effective_message.text or "").strip()
    form_fields = record.get("form_fields")
    if isinstance(form_fields, list) and form_fields:
        field, _label = form_fields[0]
        field = str(field)
        values = dict(record["values"])
        pending_dropdown = record.get("pending_dropdown")
        if isinstance(pending_dropdown, dict) and pending_dropdown.get("field") == field:
            matches = pending_dropdown.get("matches")
            if isinstance(matches, list) and text.isdigit():
                index = int(text) - 1
                if 0 <= index < len(matches):
                    values[field] = str(matches[index])
                    await update_record_fields(str(record["db_path"]), int(record["record_id"]), {field: values[field]})
                    record.pop("pending_dropdown", None)
                    record["values"] = values
                    record["form_fields"] = form_fields[1:]
                    record["missing_fields"] = manual_missing_required_fields(values) if record.get("manual_entry") else missing_required_fields(values)
                    return await _ask_next_missing_field(update, context)
                await update.effective_message.reply_text("S\u1ed1 th\u1ee9 t\u1ef1 kh\u00f4ng h\u1ee3p l\u1ec7. Vui l\u00f2ng ch\u1ecdn l\u1ea1i ho\u1eb7c nh\u1eadp t\u1eeb kh\u00f3a kh\u00e1c.")
                return ASK_MISSING_FIELD
            record.pop("pending_dropdown", None)

        if text not in ("-", "."):
            if field in TELEGRAM_DROPDOWN_FIELDS:
                options = _dropdown_options_from_context(context, field)
                matches = search_dropdown_options(text, options)
                if len(matches) == 1:
                    values[field] = matches[0]
                elif len(matches) > 1:
                    record["pending_dropdown"] = {"field": field, "matches": matches}
                    choices = "\n".join(f"{index}. {option}" for index, option in enumerate(matches, start=1))
                    header = f"Tìm thấy {len(matches)} kết quả phù hợp:\n"
                    footer = "\n\nTrả lời số thứ tự để chọn, nhập từ khóa khác để tìm lại, hoặc nhập '.' để bỏ qua."
                    full_msg = header + choices + footer
                    # Telegram giới hạn 4096 ký tự/tin nhắn → chia nhỏ nếu cần
                    MAX_MSG_LEN = 4000
                    if len(full_msg) <= MAX_MSG_LEN:
                        await update.effective_message.reply_text(full_msg)
                    else:
                        lines = choices.split("\n")
                        chunk = header
                        for line in lines:
                            if len(chunk) + len(line) + 1 > MAX_MSG_LEN:
                                await update.effective_message.reply_text(chunk)
                                chunk = ""
                            chunk += line + "\n"
                        if chunk.strip():
                            await update.effective_message.reply_text(chunk + footer)
                        else:
                            await update.effective_message.reply_text(footer)
                    return ASK_MISSING_FIELD
                else:
                    values[field] = text
                    if options:
                        await update.effective_message.reply_text("Kh\u00f4ng t\u00ecm th\u1ea5y trong danh s\u00e1ch, bot s\u1ebd l\u01b0u theo n\u1ed9i dung anh nh\u1eadp.")
            else:
                if field == "customer_info" and values.get("customer_type") == "organization":
                    from .sqlite_store import get_all_organizations
                    settings = _settings_from_context(context)
                    orgs = get_all_organizations(settings.cases_db_path)
                    for org in orgs:
                        abbrev = org.get("abbreviation") or ""
                        if abbrev.strip().lower() == text.lower() and abbrev.strip():
                            text = org.get("name") or ""
                            values["tax_code"] = org.get("tax_code") or values.get("tax_code", "")
                            values["customer_address"] = org.get("address") or values.get("customer_address", "")
                            values["representative_name"] = org.get("representative") or values.get("representative_name", "")
                            values["representative_position"] = org.get("position") or values.get("representative_position", "")
                            break
                values[field] = _normalize_customer_type(text) if field == "customer_type" else text
            synced_values = sync_hidden_gcn_fields_from_form(values)
            sync_updates = {
                sync_field: synced_values.get(sync_field, "")
                for sync_field in HIDDEN_GCN_FIELDS
                if synced_values.get(sync_field, "") != values.get(sync_field, "")
            }
            values = synced_values
            await update_record_fields(
                str(record["db_path"]),
                int(record["record_id"]),
                {field: values[field], **sync_updates},
            )
        record["values"] = values
        remaining_fields = form_fields[1:]
        if field == "customer_type":
            organization_queue = [(item_field, label) for item_field, label, _default in TELEGRAM_ORGANIZATION_FIELDS]
            remaining_fields = [
                item for item in remaining_fields if item[0] not in {org_field for org_field, _label in organization_queue}
            ]
            if values.get("customer_type") == "organization":
                remaining_fields.extend(organization_queue)
        record["form_fields"] = remaining_fields
        record["missing_fields"] = manual_missing_required_fields(values) if record.get("manual_entry") else missing_required_fields(values)
        return await _ask_next_missing_field(update, context)

    missing_fields = record.get("missing_fields")
    if not isinstance(missing_fields, list) or not missing_fields:
        return await _show_confirmation(update, context)
    field, label = missing_fields[0]
    if not text:
        await update.effective_message.reply_text(f"{label} kh\u00f4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng. Vui l\u00f2ng nh\u1eadp l\u1ea1i:")
        return ASK_MISSING_FIELD

    values = dict(record["values"])
    values[str(field)] = text
    record["values"] = values
    record["missing_fields"] = missing_fields[1:]
    await update_record_fields(str(record["db_path"]), int(record["record_id"]), {str(field): text})

    if record["missing_fields"]:
        return await _ask_next_missing_field(update, context)
    return await _show_confirmation(update, context)


async def handle_edit_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is None or update.effective_message is None:
        return ConversationHandler.END
    text = (update.effective_message.text or "").strip()
    values = dict(record.get("values") or {})
    editable_fields = editable_record_fields(values)
    if not text.isdigit():
        await update.effective_message.reply_text("Vui lòng nhập số thứ tự của mục cần sửa.")
        return EDIT_FIELD_SELECT
    index = int(text) - 1
    if index < 0 or index >= len(editable_fields):
        await update.effective_message.reply_text("Số thứ tự không hợp lệ. Vui lòng nhập lại.")
        return EDIT_FIELD_SELECT

    field, label = editable_fields[index]
    record["form_fields"] = [(field, label)]
    record["edit_mode"] = True
    record.pop("pending_dropdown", None)
    return await _ask_next_missing_field(update, context)


async def handle_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    record = _get_conversation_record(context)
    if query is None or record is None:
        return ConversationHandler.END
    await query.answer()
    record_id = int(record["record_id"])
    db_path = str(record["db_path"])
    if query.data == EDIT_CALLBACK:
        values = dict(record["values"])
        await query.edit_message_text(format_editable_field_list(values))
        return EDIT_FIELD_SELECT
    if query.data == CONFIRM_CALLBACK:
        await update_record_status(db_path, record_id, CONFIRMED_STATUS)
        settings = _settings_from_context(context)
        await sync_record_to_case(settings.records_db_path, settings.cases_db_path, record_id)
        await query.edit_message_text(f"\u0110\u00e3 x\u00e1c nh\u1eadn l\u01b0u b\u1ea3n ghi #{record_id}. Tr\u1ea1ng th\u00e1i: {CONFIRMED_STATUS}")
        if query.message is not None:
            draft = await draft_email(
                record_id,
                db_path,
                template_path=settings.email_template_path,
                to_email=settings.mail_to,
            )
            await query.message.reply_text(
                format_email_draft_message(draft),
                reply_markup=automation_keyboard(record_id),
            )
            record_for_preview = await get_record(db_path, record_id)
            preview_html = render_appraisal_email(mail_data_from_record(record_for_preview))
            await send_appraisal_email_preview(
                chat_id=query.message.chat_id,
                html=preview_html,
                context=context,
                filename=f"appraisal_email_record_{record_id}.html",
            )
    else:
        await update_record_status(db_path, record_id, CANCELLED_STATUS)
        settings = _settings_from_context(context)
        await sync_record_to_case(settings.records_db_path, settings.cases_db_path, record_id)
        await query.edit_message_text(f"\u0110\u00e3 h\u1ee7y b\u1ea3n ghi #{record_id}. Tr\u1ea1ng th\u00e1i: {CANCELLED_STATUS}")
    context.user_data.pop("pending_record", None)
    return ConversationHandler.END


async def handle_concurrent_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is not None:
        await update.effective_message.reply_text(
            "Bạn đang có một hồ sơ chưa hoàn tất. Vui lòng điền nốt thông tin cho hồ sơ hiện tại, "
            "hoặc gõ /cancel để hủy và bắt đầu quét lại các tệp mới."
        )


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is not None:
        await update_record_status(str(record["db_path"]), int(record["record_id"]), CANCELLED_STATUS)
        context.user_data.pop("pending_record", None)
    if update.effective_message is not None:
        await update.effective_message.reply_text("\u0110\u00e3 h\u1ee7y phi\u00ean x\u1eed l\u00fd GCN.")
    return ConversationHandler.END


async def _run_web_automation_task(
    *,
    application: Application,
    chat_id: int,
    record_id: int,
    settings: TelegramSettings,
) -> None:
    try:
        from .web_automation import run_company_web_entry

        record = await get_record(settings.records_db_path, record_id)
        result = await run_company_web_entry(record, web_url=settings.company_web_url)
        await application.bot.send_message(chat_id=chat_id, text=f"Nhập Web Công ty thành công:\n{result}")
    except Exception as exc:
        err_msg = str(exc)
        await application.bot.send_message(chat_id=chat_id, text=f"Nhập Web Công ty thất bại:\n{err_msg}")
        
        import re
        import os
        match = re.search(r"Ảnh lỗi:\s*(.+?\.png)", err_msg)
        if match:
            filename = match.group(1)
            filepath = os.path.join(PROJECT_ROOT, "logs", "errors", filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "rb") as f:
                        await application.bot.send_photo(chat_id=chat_id, photo=f, caption="Ảnh chụp màn hình lỗi")
                except Exception as send_exc:
                    print(f"Khong the gui anh loi len Telegram: {send_exc}")


async def handle_post_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    try:
        await query.answer()
    except Exception:
        pass
    try:
        action, raw_record_id = query.data.split(":", 1)
        record_id = int(raw_record_id)
    except ValueError:
        await query.edit_message_text("Du lieu thao tac khong hop le.")
        return

    settings = _settings_from_context(context)
    if action == SEND_MAIL_CALLBACK_PREFIX:
        try:
            record = await get_record(settings.records_db_path, record_id)
            await send_appraisal_email_service({**record, "to_email": settings.mail_to})
            
            state = context.user_data.get(f"auto_state_{record_id}", {"mail": False, "web": False})
            state["mail"] = True
            context.user_data[f"auto_state_{record_id}"] = state
            
            await query.edit_message_text(
                "\u0110\u00e3 g\u1eedi mail th\u00e0nh c\u00f4ng.",
                reply_markup=automation_keyboard(record_id, mail_done=state["mail"], web_done=state["web"])
            )
        except Exception as exc:
            state = context.user_data.get(f"auto_state_{record_id}", {"mail": False, "web": False})
            await query.edit_message_text(f"G\u1eedi mail th\u1ea5t b\u1ea1i cho b\u1ea3n ghi #{record_id}: {exc}", reply_markup=automation_keyboard(record_id, mail_done=state["mail"], web_done=state["web"]))
        return

    if action == WEB_AUTOMATION_CALLBACK_PREFIX:
        chat_id = query.message.chat_id if query.message is not None else None
        if chat_id is None:
            await query.edit_message_text("Kh\u00f4ng x\u00e1c \u0111\u1ecbnh \u0111\u01b0\u1ee3c chat \u0111\u1ec3 g\u1eedi k\u1ebft qu\u1ea3 nh\u1eadp web.")
            return
            
        state = context.user_data.get(f"auto_state_{record_id}", {"mail": False, "web": False})
        state["web"] = True
        context.user_data[f"auto_state_{record_id}"] = state
        
        create_task(
            _run_web_automation_task(
                application=context.application,
                chat_id=chat_id,
                record_id=record_id,
                settings=settings,
            )
        )
        await query.edit_message_text(f"\u0110\u00e3 b\u1eaft \u0111\u1ea7u nh\u1eadp Web C\u00f4ng ty cho b\u1ea3n ghi #{record_id}.", reply_markup=automation_keyboard(record_id, mail_done=state["mail"], web_done=state["web"]))
        return

    if action == BOTH_AUTOMATION_CALLBACK_PREFIX:
        chat_id = query.message.chat_id if query.message is not None else None
        if chat_id is None:
            await query.edit_message_text("Kh\u00f4ng x\u00e1c \u0111\u1ecbnh \u0111\u01b0\u1ee3c chat \u0111\u1ec3 g\u1eedi k\u1ebft qu\u1ea3 nh\u1eadp web.")
            return
            
        record = await get_record(settings.records_db_path, record_id)
        
        state = context.user_data.get(f"auto_state_{record_id}", {"mail": False, "web": False})
        state["mail"] = True
        state["web"] = True
        context.user_data[f"auto_state_{record_id}"] = state
        
        await query.edit_message_text(f"Đang thực hiện CẢ HAI (Mail + Web) cho bản ghi #{record_id}...", reply_markup=automation_keyboard(record_id, mail_done=True, web_done=True))
        
        async def _run_mail():
            try:
                await send_appraisal_email_service({**record, "to_email": settings.mail_to})
                await context.application.bot.send_message(chat_id=chat_id, text=f"📧 Gửi Mail Hành chính cho bản ghi #{record_id} thành công.")
            except Exception as e:
                await context.application.bot.send_message(chat_id=chat_id, text=f"📧 Gửi Mail Hành chính cho bản ghi #{record_id} thất bại: {e}")
                
        create_task(asyncio.gather(
            _run_mail(),
            _run_web_automation_task(
                application=context.application,
                chat_id=chat_id,
                record_id=record_id,
                settings=settings,
            )
        ))
        return
        
    if action == DONE_AUTOMATION_CALLBACK_PREFIX:
        await query.edit_message_text(f"✅ Đã hoàn tất quy trình cho bản ghi #{record_id}.")
        return


async def handle_other_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text("Bot hien chi tu dong quet hinh anh va tep PDF.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import logging
    logging.getLogger(__name__).error("Telegram error: %s", context.error, exc_info=context.error)


def build_telegram_application(token: str) -> Application:
    telegram_app = Application.builder().token(token).updater(None).build()
    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("nhap", start_manual_entry),
            CommandHandler("new", start_manual_entry),
            MessageHandler(filters.PHOTO, handle_photo),
            MessageHandler(filters.Document.PDF | filters.Document.FileExtension("pdf"), handle_pdf_document),
        ],
        states={
            ASK_MISSING_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_missing_field_reply),
            ],
            CONFIRMING: [
                CallbackQueryHandler(handle_confirmation_callback, pattern=f"^({CONFIRM_CALLBACK}|{CANCEL_CALLBACK}|{EDIT_CALLBACK})$"),
            ],
            EDIT_FIELD_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_field_selection),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.PHOTO | filters.Document.ALL, handle_concurrent_upload),
        ],
    )
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("nhapthucong", request_manual_template_command))
    telegram_app.add_handler(CommandHandler("chat_id", chat_id_command))
    telegram_app.add_handler(CommandHandler("listener_on", listener_on_command))
    telegram_app.add_handler(CommandHandler("listener_off", listener_off_command))
    telegram_app.add_handler(CommandHandler("listener_status", listener_status_command))
    telegram_app.add_handler(CommandHandler("listener_log", listener_log_command))
    telegram_app.add_handler(CommandHandler("gui_mail", send_mail_by_contract_command))
    telegram_app.add_handler(CommandHandler("send_mail", send_mail_by_contract_command))
    telegram_app.add_handler(CommandHandler("tra_cuu", search_case_by_contract_command))
    telegram_app.add_handler(CommandHandler("search", search_case_by_contract_command))
    telegram_app.add_handler(conversation)
    telegram_app.add_handler(
        CallbackQueryHandler(
            handle_post_confirm_action,
            pattern=f"^({SEND_MAIL_CALLBACK_PREFIX}|{WEB_AUTOMATION_CALLBACK_PREFIX}|{BOTH_AUTOMATION_CALLBACK_PREFIX}|{DONE_AUTOMATION_CALLBACK_PREFIX}):\\d+$",
        )
    )
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_other_document))
    telegram_app.add_error_handler(error_handler)
    return telegram_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_telegram_settings()
    log_records_db_path("telegram_server", settings.records_db_path)
    await init_records_db(settings.records_db_path)
    telegram_app = build_telegram_application(settings.bot_token)
    telegram_app.bot_data["settings"] = settings
    if settings.excel_template_path and os.path.exists(settings.excel_template_path):
        try:
            telegram_app.bot_data["excel_dropdown_options"] = load_dropdown_options(settings.excel_template_path)
        except Exception:
            telegram_app.bot_data["excel_dropdown_options"] = {}
    else:
        telegram_app.bot_data["excel_dropdown_options"] = {}
    app.state.telegram_app = telegram_app
    app.state.telegram_settings = settings

    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(
        url=settings.webhook_endpoint,
        allowed_updates=Update.ALL_TYPES,
    )
    await telegram_app.start()
    try:
        yield
    finally:
        await telegram_app.stop()
        await telegram_app.shutdown()


app = FastAPI(title="Telegram Bot Webhook", lifespan=lifespan)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(TELEGRAM_WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> dict[str, bool]:
    telegram_app: Application | None = getattr(request.app.state, "telegram_app", None)
    if telegram_app is None:
        raise HTTPException(status_code=503, detail="Telegram bot chua san sang.")

    payload = await request.json()
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

