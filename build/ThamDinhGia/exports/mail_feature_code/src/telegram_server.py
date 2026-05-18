from __future__ import annotations

import os
import re
import smtplib
import subprocess
import sys
import unicodedata
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
from .models import LandCertificateExtraction, blank_extraction
from .mail_listener import (
    DEFAULT_LOG_PATH as MAIL_LISTENER_LOG_PATH,
    listener_status_summary,
    read_recent_listener_logs,
    set_listener_enabled,
    write_listener_pid,
)


TELEGRAM_WEBHOOK_PATH = "/webhook/telegram"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploads")
DEFAULT_RECORDS_DB = os.path.join(PROJECT_ROOT, "data", "telegram_records.db")
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
REQUIRED_RECORD_FIELDS = [
    ("so_to", "Số tờ bản đồ"),
    ("so_thua", "Số thửa đất"),
    ("chu_so_huu", "Chủ sở hữu"),
]
TELEGRAM_FORM_FIELDS = [
    ("customer_type", "Loại khách hàng", "individual"),
    ("contract_number", "Số hợp đồng", ""),
    ("asset_type", "Loại tài sản", "BĐS đặc thù khác"),
    ("asset_description", "Tài sản thẩm định giá", ""),
    ("preliminary_status", "Sơ bộ", "Chưa sơ bộ"),
    ("expected_finish_date", "Thời gian dự kiến hoàn thành", ""),
    ("valuation_purpose", "Mục đích thẩm định", ""),
    ("source", "Nguồn/đối tác", ""),
    ("customer_info", "Thông tin khách hàng", ""),
    ("customer_address", "Địa chỉ khách hàng", ""),
    ("citizen_id", "Số CCCD/CMND", ""),
    ("valuation_fee_number", "Phí thẩm định", ""),
    ("advance_payment", "Tạm ứng", "0"),
    ("survey_cost", "Chi phí khảo sát", "0"),
    ("valuation_staff", "Chuyên viên nghiệp vụ", ""),
    ("personal_note", "Ghi chú cá nhân", ""),
]
TELEGRAM_ORGANIZATION_FIELDS = [
    ("tax_code", "Mã số thuế", ""),
    ("representative_name", "Người đại diện", ""),
    ("representative_position", "Chức vụ người đại diện", ""),
    ("handover_contact_name", "Người nhận bàn giao", ""),
    ("handover_contact_position", "Chức vụ người nhận bàn giao", ""),
    ("handover_contact_phone", "Điện thoại người nhận bàn giao", ""),
    ("authorization_note", "Căn cứ/giấy ủy quyền đại diện", ""),
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
MAX_DROPDOWN_MATCHES = 6


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
    load_dotenv(os.path.join(PROJECT_ROOT, "API.env"))
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    upload_dir = os.getenv("TELEGRAM_UPLOAD_DIR", DEFAULT_UPLOAD_DIR).strip() or DEFAULT_UPLOAD_DIR
    records_db_path = os.getenv("TELEGRAM_RECORDS_DB", DEFAULT_RECORDS_DB).strip() or DEFAULT_RECORDS_DB
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
    return re.sub(r"\s+", " ", without_marks.lower()).strip()


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
    return [option for _score, _index, option in scored[:limit]]


def _unique_upload_path(upload_dir: str, file_name: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = _safe_file_name(file_name)
    stem, suffix = os.path.splitext(safe_name)
    return os.path.join(upload_dir, f"{uuid4().hex}_{stem}{suffix}")


async def init_records_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                so_thua TEXT NOT NULL DEFAULT '',
                so_to TEXT NOT NULL DEFAULT '',
                dia_chi TEXT NOT NULL DEFAULT '',
                chu_so_huu TEXT NOT NULL DEFAULT '',
                customer_type TEXT NOT NULL DEFAULT 'individual',
                contract_number TEXT NOT NULL DEFAULT '',
                asset_type TEXT NOT NULL DEFAULT '',
                asset_description TEXT NOT NULL DEFAULT '',
                preliminary_status TEXT NOT NULL DEFAULT '',
                expected_finish_date TEXT NOT NULL DEFAULT '',
                valuation_purpose TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                customer_info TEXT NOT NULL DEFAULT '',
                customer_address TEXT NOT NULL DEFAULT '',
                citizen_id TEXT NOT NULL DEFAULT '',
                valuation_fee_number TEXT NOT NULL DEFAULT '',
                advance_payment TEXT NOT NULL DEFAULT '',
                survey_cost TEXT NOT NULL DEFAULT '',
                valuation_staff TEXT NOT NULL DEFAULT '',
                personal_note TEXT NOT NULL DEFAULT '',
                tax_code TEXT NOT NULL DEFAULT '',
                representative_name TEXT NOT NULL DEFAULT '',
                representative_position TEXT NOT NULL DEFAULT '',
                authorization_note TEXT NOT NULL DEFAULT '',
                handover_contact_name TEXT NOT NULL DEFAULT '',
                handover_contact_position TEXT NOT NULL DEFAULT '',
                handover_contact_phone TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(records)")
        existing_columns = {str(row[1]) for row in await cursor.fetchall()}
        for column in sorted(TELEGRAM_RECORD_TEXT_COLUMNS):
            if column not in existing_columns:
                default_sql = "'individual'" if column == "customer_type" else "''"
                await db.execute(f"ALTER TABLE records ADD COLUMN {column} TEXT NOT NULL DEFAULT {default_sql}")
        await db.commit()


async def save_record(db_path: str, file_path: str, extraction: LandCertificateExtraction) -> int:
    form_values = extraction_to_record_values(extraction)
    async with aiosqlite.connect(db_path) as db:
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
        cursor = await db.execute(
            """
            INSERT INTO records (
                file_path, so_thua, so_to, dia_chi, chu_so_huu,
                customer_type, asset_type, asset_description, preliminary_status,
                customer_info, customer_address, citizen_id, advance_payment, survey_cost,
                expected_finish_date,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_path,
                form_values["so_thua"],
                form_values["so_to"],
                form_values["dia_chi"],
                form_values["chu_so_huu"],
                form_values["customer_type"],
                form_values["asset_type"],
                form_values["asset_description"],
                form_values["preliminary_status"],
                form_values["customer_info"],
                form_values["customer_address"],
                form_values["citizen_id"],
                form_values["advance_payment"],
                form_values["survey_cost"],
                form_values["expected_finish_date"],
                PENDING_STATUS,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def update_record_fields(db_path: str, record_id: int, values: dict[str, str]) -> None:
    allowed_fields = {"so_thua", "so_to", "dia_chi", "chu_so_huu"} | TELEGRAM_RECORD_TEXT_COLUMNS
    updates = {field: value for field, value in values.items() if field in allowed_fields}
    if not updates:
        return
    assignments = ", ".join(f"{field} = ?" for field in updates)
    params = [*updates.values(), record_id]
    async with aiosqlite.connect(db_path) as db:
        await db.execute(f"UPDATE records SET {assignments} WHERE id = ?", params)
        await db.commit()


async def update_record_status(db_path: str, record_id: int, status: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE records SET status = ? WHERE id = ?", (status, record_id))
        await db.commit()


async def get_record(db_path: str, record_id: int) -> dict[str, str]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM records
            WHERE id = ?
            """,
            (record_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        raise ValueError(f"Khong tim thay ban ghi #{record_id}.")
    return {key: str(row[key] or "") for key in row.keys()}


async def get_record_by_contract_number(db_path: str, contract_query: str) -> dict[str, str] | None:
    query = (contract_query or "").strip()
    if not query:
        return None
    short_query = short_contract_number(query)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM records
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


async def get_case_by_contract_number(db_path: str, contract_query: str) -> dict[str, str] | None:
    query = (contract_query or "").strip()
    if not query or not os.path.exists(db_path):
        return None
    short_query = short_contract_number(query)
    async with aiosqlite.connect(db_path) as db:
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


def automation_keyboard(record_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🚀 Gửi Mail", callback_data=f"{SEND_MAIL_CALLBACK_PREFIX}:{record_id}"),
                InlineKeyboardButton("🖥️ Nhập Web Công ty", callback_data=f"{WEB_AUTOMATION_CALLBACK_PREFIX}:{record_id}"),
            ]
        ]
    )


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


def extraction_to_record_values(extraction: LandCertificateExtraction) -> dict[str, str]:
    so_thua = extraction.so_thua_dat.value.strip()
    so_to = extraction.so_to_ban_do.value.strip()
    dia_chi = extraction.dia_chi_thua_dat.value.strip()
    chu_so_huu = extraction.ten_chu_so_huu_cuoi_cung.value.strip()
    owner_address = extraction.dia_chi_chu_so_huu_cuoi_cung.value.strip()
    citizen_id = extraction.so_cccd_chu_so_huu_cuoi_cung.value.strip()
    asset_description_parts = []
    if so_thua:
        asset_description_parts.append(f"Thửa đất số {so_thua}")
    if so_to:
        asset_description_parts.append(f"tờ bản đồ số {so_to}")
    asset_description = ", ".join(asset_description_parts)
    if dia_chi:
        asset_description = f"{asset_description}; tại địa chỉ {dia_chi}." if asset_description else f"Thửa đất tại địa chỉ {dia_chi}."
    values = _default_form_values()
    values.update({
        "so_thua": extraction.so_thua_dat.value.strip(),
        "so_to": extraction.so_to_ban_do.value.strip(),
        "dia_chi": extraction.dia_chi_thua_dat.value.strip(),
        "chu_so_huu": extraction.ten_chu_so_huu_cuoi_cung.value.strip(),
        "customer_type": "individual",
        "asset_type": "BĐS đặc thù khác",
        "asset_description": asset_description,
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
        ("so_thua", "Số thửa"),
        ("so_to", "Số tờ bản đồ"),
        ("dia_chi", "Địa chỉ thửa đất"),
        ("chu_so_huu", "Chủ sở hữu"),
    ]
    fields.extend(
        (field, label)
        for field, label, _default in TELEGRAM_FORM_FIELDS
        if field not in TELEGRAM_SKIPPED_FORM_FIELDS
    )
    if values.get("customer_type") == "organization":
        fields.extend((field, label) for field, label, _default in TELEGRAM_ORGANIZATION_FIELDS)
    return fields


def format_editable_field_list(values: dict[str, str]) -> str:
    lines = ["Anh muốn sửa mục nào? Trả lời số thứ tự của mục cần sửa:"]
    for index, (field, label) in enumerate(editable_record_fields(values), start=1):
        value = values.get(field) or "Chưa có"
        if field == "contract_number":
            value = short_contract_number(value, fallback="Chưa có")
        lines.append(f"{index}. {label}: {value}")
    return "\n".join(lines)


def _default_form_values() -> dict[str, str]:
    values = {field: default for field, _label, default in TELEGRAM_FORM_FIELDS}
    values.update({field: default for field, _label, default in TELEGRAM_ORGANIZATION_FIELDS})
    return values


def _normalize_customer_type(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"organization", "to chuc", "tổ chức", "doanh nghiep", "doanh nghiệp", "cong ty", "công ty"}:
        return "organization"
    if lowered in {"individual", "ca nhan", "cá nhân"}:
        return "individual"
    return value.strip()


def _field_label(field_name: str) -> str:
    for field, label, _default in [*TELEGRAM_FORM_FIELDS, *TELEGRAM_ORGANIZATION_FIELDS]:
        if field == field_name:
            return label
    for field, label in REQUIRED_RECORD_FIELDS:
        if field == field_name:
            return label
    return field_name


def format_extraction_response(record_id: int, extraction: LandCertificateExtraction) -> str:
    return "\n".join(
        [
            f"Da quet GCN va luu ban ghi #{record_id}.",
            "",
            f"So thua: {extraction.so_thua_dat.value or 'Chua doc duoc'}",
            f"So to ban do: {extraction.so_to_ban_do.value or 'Chua doc duoc'}",
            f"Dia chi thua dat: {extraction.dia_chi_thua_dat.value or 'Chua doc duoc'}",
            f"Chu so huu: {extraction.ten_chu_so_huu_cuoi_cung.value or 'Chua doc duoc'}",
            f"Trang thai: {PENDING_STATUS}",
        ]
    )


def format_record_summary(record_id: int, values: dict[str, str]) -> str:
    lines = [
        f"Thông tin hồ sơ #{record_id}:",
        "",
    ]
    for index, (field, label) in enumerate(editable_record_fields(values), start=1):
        value = values.get(field) or "Chưa có"
        if field == "contract_number":
            value = short_contract_number(value, fallback="Chưa có")
        lines.append(f"{index}. {label}: {value}")
    lines.append(f"Trạng thái: {PENDING_STATUS}")
    return "\n".join(lines)


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Sửa thông tin", callback_data=EDIT_CALLBACK),
            ],
            [
                InlineKeyboardButton("✅ Xác nhận lưu", callback_data=CONFIRM_CALLBACK),
                InlineKeyboardButton("❌ Hủy bỏ", callback_data=CANCEL_CALLBACK),
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
        hint = (
            f"Giá trị hiện tại: {current_value}\n"
            "Nhập giá trị mới, hoặc nhập '-' để giữ nguyên/bỏ qua."
            if current_value
            else "Nhập giá trị, hoặc nhập '-' để bỏ qua."
        )
        if field == "customer_type":
            hint += "\nGợi ý: nhập 'cá nhân' hoặc 'tổ chức'."
        if str(field) in TELEGRAM_DROPDOWN_FIELDS:
            hint += "\nĐây là trường có danh sách chọn. Nhập từ khóa, bot sẽ tìm gợi ý phù hợp."
        await update.effective_message.reply_text(f"{label}:\n{hint}")
        return ASK_MISSING_FIELD
    missing_fields = record.get("missing_fields")
    if not isinstance(missing_fields, list) or not missing_fields:
        return await _show_confirmation(update, context)
    _field, label = missing_fields[0]
    await update.effective_message.reply_text(f"Thiếu {label}. Vui lòng nhập bổ sung:")
    return ASK_MISSING_FIELD


async def _show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is None or update.effective_message is None:
        return ConversationHandler.END
    record_id = int(record["record_id"])
    values = dict(record["values"])
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
) -> tuple[int, str, LandCertificateExtraction]:
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
    await update.effective_message.reply_text(f"Đã lưu TELEGRAM_CHAT_ID={chat_id} vào API.env.")


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
    enabled_text = "Bật" if status.get("enabled") else "Tắt"
    running_text = "Đang chạy" if status.get("running") else "Chưa chạy"
    pid_text = status.get("pid") or "Không có"
    return (
        "Trạng thái Mail Listener:\n"
        f"- Theo dõi Gmail: {enabled_text}\n"
        f"- Tiến trình nền: {running_text}\n"
        f"- PID: {pid_text}\n"
        f"- Log: {MAIL_LISTENER_LOG_PATH}"
    )


def _format_listener_logs(limit: int = 10) -> str:
    logs = read_recent_listener_logs(limit)
    if not logs:
        return "Chưa có log Mail Listener."
    lines = ["10 dòng log Mail Listener gần nhất:"]
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
            f"Đã bật Mail Listener và đảm bảo tiến trình nền đang chạy. PID: {pid}\n\n{_format_listener_status()}"
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Bật Mail Listener thất bại: {exc}")


async def listener_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    try:
        set_listener_enabled(False, updated_by=_listener_updated_by(update))
        await update.effective_message.reply_text(
            "Đã tắt theo dõi Gmail. Tiến trình nền vẫn có thể còn chạy nhưng sẽ bỏ qua các vòng quét mới.\n\n"
            f"{_format_listener_status()}"
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Tắt Mail Listener thất bại: {exc}")


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
        await send_appraisal_email_service({**record, "to_email": settings.mail_to})
        contract_label = short_contract_number(record.get("contract_number"), fallback=short_query)
        source_label = "quản lý hồ sơ" if record_source == "cases" else "Telegram"
        await update.effective_message.reply_text(f"Đã gửi mail thành công cho hồ sơ {contract_label} từ {source_label}.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Gửi mail thất bại cho hồ sơ {short_query}: {exc}")


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
        record["form_fields"] = editable_record_fields(values)
        record["missing_fields"] = []
        record.pop("pending_dropdown", None)

    await update.effective_message.reply_text(
        f"Da tao ho so nhap thu cong #{record_id}. Bot se hoi tung thong tin can dien."
    )
    return await _ask_next_missing_field(update, context)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    text = update.effective_message.text or ""
    await update.effective_message.reply_text(f"Da nhan tin nhan: {text}")


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    if not update.effective_message.photo:
        await update.effective_message.reply_text("Khong tim thay hinh anh trong tin nhan.")
        return ConversationHandler.END
    await update.effective_message.reply_text("Da nhan hinh anh, dang quet GCN bang Gemini...")
    try:
        settings = _settings_from_context(context)
        photo = update.effective_message.photo[-1]
        record_id, _upload_path, extraction = await process_land_certificate_file(
            file_ref=photo,
            file_name=f"{photo.file_unique_id}.jpg",
            settings=settings,
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Quet GCN that bai: {exc}")
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
    await update.effective_message.reply_text(f"Da nhan {file_name}, dang quet GCN bang Gemini...")
    try:
        settings = _settings_from_context(context)
        record_id, _upload_path, extraction = await process_land_certificate_file(
            file_ref=document,
            file_name=file_name,
            settings=settings,
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Quet GCN that bai: {exc}")
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
                    record["missing_fields"] = missing_required_fields(values)
                    return await _ask_next_missing_field(update, context)
                await update.effective_message.reply_text("Số thứ tự không hợp lệ. Vui lòng chọn lại hoặc nhập từ khóa khác.")
                return ASK_MISSING_FIELD
            record.pop("pending_dropdown", None)

        if text != "-":
            if field in TELEGRAM_DROPDOWN_FIELDS:
                options = _dropdown_options_from_context(context, field)
                matches = search_dropdown_options(text, options)
                if len(matches) == 1:
                    values[field] = matches[0]
                elif len(matches) > 1:
                    record["pending_dropdown"] = {"field": field, "matches": matches}
                    choices = "\n".join(f"{index}. {option}" for index, option in enumerate(matches, start=1))
                    await update.effective_message.reply_text(
                        f"Tìm thấy {len(matches)} kết quả phù hợp:\n{choices}\n\n"
                        "Trả lời số thứ tự để chọn, nhập từ khóa khác để tìm lại, hoặc nhập '-' để bỏ qua."
                    )
                    return ASK_MISSING_FIELD
                else:
                    values[field] = text
                    if options:
                        await update.effective_message.reply_text("Không tìm thấy trong danh sách, bot sẽ lưu theo nội dung anh nhập.")
            else:
                values[field] = _normalize_customer_type(text) if field == "customer_type" else text
            await update_record_fields(str(record["db_path"]), int(record["record_id"]), {field: values[field]})
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
        record["missing_fields"] = missing_required_fields(values)
        return await _ask_next_missing_field(update, context)

    missing_fields = record.get("missing_fields")
    if not isinstance(missing_fields, list) or not missing_fields:
        return await _show_confirmation(update, context)
    field, label = missing_fields[0]
    if not text:
        await update.effective_message.reply_text(f"{label} không được để trống. Vui lòng nhập lại:")
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
        await query.edit_message_text(f"Đã xác nhận lưu bản ghi #{record_id}. Trạng thái: {CONFIRMED_STATUS}")
        if query.message is not None:
            settings = _settings_from_context(context)
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
        await query.edit_message_text(f"Đã hủy bản ghi #{record_id}. Trạng thái: {CANCELLED_STATUS}")
    context.user_data.pop("pending_record", None)
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    record = _get_conversation_record(context)
    if record is not None:
        await update_record_status(str(record["db_path"]), int(record["record_id"]), CANCELLED_STATUS)
        context.user_data.pop("pending_record", None)
    if update.effective_message is not None:
        await update.effective_message.reply_text("Đã hủy phiên xử lý GCN.")
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
        await application.bot.send_message(chat_id=chat_id, text=f"Nhập Web Công ty thành công: {result}")
    except Exception as exc:
        await application.bot.send_message(chat_id=chat_id, text=f"Nhập Web Công ty thất bại: {exc}")


async def handle_post_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
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
            await query.edit_message_text("Đã gửi mail thành công")
        except Exception as exc:
            await query.edit_message_text(f"Gửi mail thất bại cho bản ghi #{record_id}: {exc}")
        return

    if action == WEB_AUTOMATION_CALLBACK_PREFIX:
        chat_id = query.message.chat_id if query.message is not None else None
        if chat_id is None:
            await query.edit_message_text("Không xác định được chat để gửi kết quả nhập web.")
            return
        create_task(
            _run_web_automation_task(
                application=context.application,
                chat_id=chat_id,
                record_id=record_id,
                settings=settings,
            )
        )
        await query.edit_message_text(f"Đã bắt đầu nhập Web Công ty cho bản ghi #{record_id}.")


async def handle_other_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text("Bot hien chi tu dong quet hinh anh va tep PDF.")


def build_telegram_application(token: str) -> Application:
    telegram_app = Application.builder().token(token).updater(None).build()
    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("nhap", start_manual_entry),
            CommandHandler("new", start_manual_entry),
            MessageHandler(filters.PHOTO, handle_photo_message),
            MessageHandler(filters.Document.PDF, handle_pdf_document),
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
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("chat_id", chat_id_command))
    telegram_app.add_handler(CommandHandler("listener_on", listener_on_command))
    telegram_app.add_handler(CommandHandler("listener_off", listener_off_command))
    telegram_app.add_handler(CommandHandler("listener_status", listener_status_command))
    telegram_app.add_handler(CommandHandler("listener_log", listener_log_command))
    telegram_app.add_handler(CommandHandler("gui_mail", send_mail_by_contract_command))
    telegram_app.add_handler(CommandHandler("send_mail", send_mail_by_contract_command))
    telegram_app.add_handler(conversation)
    telegram_app.add_handler(
        CallbackQueryHandler(
            handle_post_confirm_action,
            pattern=f"^({SEND_MAIL_CALLBACK_PREFIX}|{WEB_AUTOMATION_CALLBACK_PREFIX}):\\d+$",
        )
    )
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_other_document))
    return telegram_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_telegram_settings()
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
