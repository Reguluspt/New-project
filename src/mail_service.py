from __future__ import annotations

import os
import re
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from typing import Any, Mapping

import asyncio
import smtplib
from dotenv import load_dotenv

from .contracts import expand_contract_number
from .mail_renderer import MailData, mail_data_from_record, render_appraisal_email
from .database_manager import log_records_db_path, resolve_records_db_path, save_outbound_message


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587


@dataclass(frozen=True)
class MailSendResult:
    to_email: str
    subject: str
    cc_emails: list[str]
    message_id: str = ""


@dataclass(frozen=True)
class GmailSmtpSettings:
    host: str
    port: int
    username: str
    password: str
    mail_from: str
    mail_to: str
    mail_cc: list[str]
    admin_email: str = ""
    professional_dept_email: str = ""
    management_cc: list[str] | None = None
    control_board_cc: list[str] | None = None
    monitor_cc_list: list[str] | None = None


def _load_env() -> None:
    import sys
    if "unittest" in sys.modules or "pytest" in sys.modules:
        return
    load_dotenv(PROJECT_ROOT / "API.env", override=True)


def _clean_header(value: object) -> str:
    if not value:
        return ""
    # Aggressively remove all newlines and tabs to prevent EmailMessage errors
    return re.sub(r"[\r\n\t]+", " ", str(value)).strip()



def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


def _parse_email_list(value: str) -> list[str]:
    return [email.strip() for email in value.split(",") if email.strip()]


def _dedupe_emails(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        email = value.strip()
        key = email.casefold()
        if email and key not in seen:
            seen.add(key)
            result.append(email)
    return result


def load_gmail_smtp_settings() -> GmailSmtpSettings:
    _load_env()
    username = os.getenv("SMTP_USERNAME", os.getenv("MAIL_USERNAME", "")).strip()
    password = os.getenv("SMTP_PASSWORD", os.getenv("MAIL_PASSWORD", "")).strip()
    mail_from = os.getenv("MAIL_FROM", "").strip() or username
    
    # Repair mojibake in mail_from if any (e.g. UTF-8 interpreted as Latin-1 / CP1252)
    try:
        if any(c in mail_from for c in "Æ°á»›º¡"):
            mail_from = mail_from.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    try:
        if any(c in mail_from for c in "Æ°á»›º¡"):
            mail_from = mail_from.encode('cp1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    if mail_from and "@" not in mail_from and username:
        mail_from = formataddr((mail_from, username))
    management_cc = _parse_email_list(os.getenv("MANAGEMENT_CC", ""))
    control_board_cc = _parse_email_list(os.getenv("CONTROL_BOARD_CC", ""))
    monitor_cc_list = _dedupe_emails([*management_cc, *control_board_cc])
    return GmailSmtpSettings(
        host=os.getenv("SMTP_HOST", os.getenv("MAIL_SERVER", DEFAULT_SMTP_HOST)).strip() or DEFAULT_SMTP_HOST,
        port=_int_env("SMTP_PORT", _int_env("MAIL_PORT", DEFAULT_SMTP_PORT)),
        username=username,
        password=password,
        mail_from=mail_from,
        mail_to=os.getenv("MAIL_TO", "").strip(),
        mail_cc=_parse_email_list(os.getenv("MAIL_CC", "")),
        admin_email=os.getenv("ADMIN_EMAIL", os.getenv("MAIL_TO", "")).strip(),
        professional_dept_email=os.getenv("PROFESSIONAL_DEPT_EMAIL", "").strip(),
        management_cc=management_cc,
        control_board_cc=control_board_cc,
        monitor_cc_list=monitor_cc_list,
    )


def _mail_data_from_payload(data_dict: Mapping[str, Any]) -> MailData:
    direct_fields = set(MailData.model_fields) - {"customer_info"}
    direct_payload = {
        field: str(data_dict.get(field) or "")
        for field in direct_fields
        if data_dict.get(field) is not None
    }
    mapped = mail_data_from_record(dict(data_dict))
    return mapped.model_copy(update=direct_payload)


def _recipient_from_payload(data_dict: Mapping[str, Any], settings: GmailSmtpSettings) -> str:
    if data_dict.get("allow_recipient_override"):
        explicit = str(data_dict.get("to_email") or data_dict.get("recipient_email") or data_dict.get("mail_to") or "").strip()
        if explicit:
            return explicit
    return str(settings.admin_email or settings.mail_to or "").strip()


def _subject_from_payload(data_dict: Mapping[str, Any], mail_data: MailData) -> str:
    explicit_subject = str(data_dict.get("subject") or "").strip()
    if explicit_subject:
        return explicit_subject
    source = _remove_phone_numbers(str(data_dict.get("source") or mail_data.source or "").strip())
    asset_description = _subject_asset_text(str(data_dict.get("asset_description") or mail_data.asset_description or "").strip())
    contract_number = str(data_dict.get("contract_number") or mail_data.contract_id or "").strip()
    prefix = f"[{expand_contract_number(contract_number)}]" if contract_number else "[XIN SỐ]"
    parts = [prefix]
    if source:
        parts.append(source)
    if asset_description:
        parts.append(asset_description.rstrip("."))
    if len(parts) == 1:
        parts.append(mail_data.contract_id or mail_data.customer_info or "Hồ sơ thẩm định")
    return " - ".join(parts) + "."


def _subject_asset_text(asset_description: str) -> str:
    first_asset = next((line.strip() for line in str(asset_description or "").splitlines() if line.strip()), "")
    if not first_asset:
        return ""
    patterns = [
        r"(?:tại\s+)?địa\s+chỉ\s*[:：]?\s*(.+)$",
        r"tại\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, first_asset, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .;")
    return first_asset.strip(" .;")


def _remove_phone_numbers(value: str) -> str:
    cleaned = re.sub(r"\s*[-–—]?\s*(?:\+?84|0)\d(?:[\s.\-]?\d){7,10}\b", "", value or "")
    return re.sub(r"\s{2,}", " ", cleaned).strip(" -–—")


def render_mail_html(data_dict: Mapping[str, Any]) -> str:
    return render_appraisal_email(_mail_data_from_payload(data_dict))


def attach_inline_logo(message: EmailMessage) -> None:
    logo_path = PROJECT_ROOT / "src" / "templates" / "logo.jpg"
    if not logo_path.exists():
        return
    html_part = message.get_payload()[-1]
    with logo_path.open("rb") as logo_file:
        html_part.add_related(
            logo_file.read(),
            maintype="image",
            subtype="jpeg",
            cid="<logo_cenvalue>",
            filename="logo.jpg",
        )


def _send_sync(message: EmailMessage, recipients: list[str], settings: GmailSmtpSettings) -> None:
    from email.utils import parseaddr
    envelope_from = parseaddr(settings.mail_from)[1] or settings.mail_from.strip()
    envelope_to = [parseaddr(r)[1] or r.strip() for e in recipients for r in e.split(",") if r.strip()]
    envelope_to = _dedupe_emails(envelope_to)
    
    with smtplib.SMTP(settings.host, settings.port, timeout=30) as smtp:
        smtp.starttls()
        if settings.username and settings.password:
            smtp.login(settings.username, settings.password)
        smtp.send_message(message, from_addr=envelope_from, to_addrs=envelope_to)


async def send_appraisal_email(data_dict: Mapping[str, Any]) -> MailSendResult:
    settings = load_gmail_smtp_settings()
    mail_data = _mail_data_from_payload(data_dict)
    to_email = _recipient_from_payload(data_dict, settings)
    subject = _subject_from_payload(data_dict, mail_data)
    cc_emails = _dedupe_emails(list(settings.monitor_cc_list or []))

    # --- BẮT ĐẦU TÍCH HỢP OAUTH2 ---
    from .oauth2_service import is_oauth_enabled, send_email_via_oauth2
    
    provider = None
    if is_oauth_enabled("google"):
        provider = "google"
    elif is_oauth_enabled("outlook"):
        provider = "outlook"
        
    if provider:
        html = render_appraisal_email(mail_data)
        try:
            print(f"Sending appraisal email using OAuth2 API for provider: {provider}")
            oauth_msg_id = await send_email_via_oauth2(
                provider=provider,
                from_email=settings.mail_from or settings.username,
                to_email=to_email,
                subject=subject,
                html_body=html,
                cc_emails=cc_emails,
            )
            record_id = str(data_dict.get("record_id") or data_dict.get("id") or "").strip()
            db_path = resolve_records_db_path(data_dict.get("records_db_path"))
            if record_id:
                log_records_db_path("mail_service", db_path)
                await save_outbound_message(db_path, record_id, message_id=oauth_msg_id, subject=subject)
            return MailSendResult(to_email=to_email, subject=subject, cc_emails=cc_emails, message_id=oauth_msg_id)
        except Exception as exc:
            print(f"OAuth2 sending failed: {exc}, falling back to SMTP.")
    # --- KẾT THÚC TÍCH HỢP OAUTH2 ---

    message_id = make_msgid(domain="gmail.com")
    missing = [
        name
        for name, value in {
            "SMTP_USERNAME/MAIL_USERNAME": settings.username,
            "SMTP_PASSWORD/MAIL_PASSWORD": settings.password,
            "MAIL_FROM": settings.mail_from,
            "ADMIN_EMAIL/MAIL_TO": to_email,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thiếu cấu hình gửi mail: {', '.join(missing)}")

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = message_id
    if cc_emails:
        message["Cc"] = ", ".join(cc_emails)
    html = render_appraisal_email(mail_data)
    message.set_content("Email này cần trình đọc HTML để xem bảng thông tin hồ sơ.")
    message.add_alternative(html, subtype="html")
    attach_inline_logo(message)
    to_emails = [addr.strip() for addr in to_email.split(",") if addr.strip()]
    recipients = _dedupe_emails([*to_emails, *cc_emails])

    await asyncio.to_thread(_send_sync, message, recipients, settings)
    record_id = str(data_dict.get("record_id") or data_dict.get("id") or "").strip()
    db_path = resolve_records_db_path(data_dict.get("records_db_path"))
    if record_id:
        log_records_db_path("mail_service", db_path)
        await save_outbound_message(db_path, record_id, message_id=message_id, subject=subject)
    return MailSendResult(to_email=to_email, subject=subject, cc_emails=cc_emails, message_id=message_id)
