from __future__ import annotations

import os
import re
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any, Mapping

import aiosmtplib
from dotenv import load_dotenv

from .mail_renderer import MailData, mail_data_from_record, render_appraisal_email


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587


@dataclass(frozen=True)
class MailSendResult:
    to_email: str
    subject: str
    cc_emails: list[str]


@dataclass(frozen=True)
class GmailSmtpSettings:
    host: str
    port: int
    username: str
    password: str
    mail_from: str
    mail_to: str
    mail_cc: list[str]


def _load_env() -> None:
    load_dotenv(PROJECT_ROOT / "API.env")
    load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


def _parse_email_list(value: str) -> list[str]:
    return [email.strip() for email in value.split(",") if email.strip()]


def load_gmail_smtp_settings() -> GmailSmtpSettings:
    _load_env()
    username = os.getenv("SMTP_USERNAME", os.getenv("MAIL_USERNAME", "")).strip()
    password = os.getenv("SMTP_PASSWORD", os.getenv("MAIL_PASSWORD", "")).strip()
    mail_from = os.getenv("MAIL_FROM", "").strip() or username
    if mail_from and "@" not in mail_from and username:
        mail_from = formataddr((mail_from, username))
    return GmailSmtpSettings(
        host=os.getenv("SMTP_HOST", os.getenv("MAIL_SERVER", DEFAULT_SMTP_HOST)).strip() or DEFAULT_SMTP_HOST,
        port=_int_env("SMTP_PORT", _int_env("MAIL_PORT", DEFAULT_SMTP_PORT)),
        username=username,
        password=password,
        mail_from=mail_from,
        mail_to=os.getenv("MAIL_TO", "").strip(),
        mail_cc=_parse_email_list(os.getenv("MAIL_CC", "")),
    )


def _mail_data_from_payload(data_dict: Mapping[str, Any]) -> MailData:
    direct_fields = set(MailData.model_fields)
    direct_payload = {
        field: str(data_dict.get(field) or "")
        for field in direct_fields
        if data_dict.get(field) is not None
    }
    mapped = mail_data_from_record(dict(data_dict))
    return mapped.model_copy(update=direct_payload)


def _recipient_from_payload(data_dict: Mapping[str, Any], settings: GmailSmtpSettings) -> str:
    return str(
        data_dict.get("to_email")
        or data_dict.get("recipient_email")
        or data_dict.get("mail_to")
        or settings.mail_to
        or ""
    ).strip()


def _subject_from_payload(data_dict: Mapping[str, Any], mail_data: MailData) -> str:
    explicit_subject = str(data_dict.get("subject") or "").strip()
    if explicit_subject:
        return explicit_subject
    source = _remove_phone_numbers(str(data_dict.get("source") or mail_data.source or "").strip())
    asset_description = str(data_dict.get("asset_description") or mail_data.asset_description or "").strip()
    parts = ["[XIN SỐ]"]
    if source:
        parts.append(source)
    if asset_description:
        parts.append(asset_description.rstrip("."))
    if len(parts) == 1:
        parts.append(mail_data.contract_id or mail_data.customer_info or "Hồ sơ thẩm định")
    return " - ".join(parts) + "."


def _remove_phone_numbers(value: str) -> str:
    cleaned = re.sub(r"\s*[-–—]?\s*(?:\+?84|0)\d(?:[\s.\-]?\d){7,10}\b", "", value or "")
    return re.sub(r"\s{2,}", " ", cleaned).strip(" -–—")


def render_mail_html(data_dict: Mapping[str, Any]) -> str:
    return render_appraisal_email(_mail_data_from_payload(data_dict))


async def send_appraisal_email(data_dict: Mapping[str, Any]) -> MailSendResult:
    settings = load_gmail_smtp_settings()
    mail_data = _mail_data_from_payload(data_dict)
    to_email = _recipient_from_payload(data_dict, settings)
    subject = _subject_from_payload(data_dict, mail_data)

    missing = [
        name
        for name, value in {
            "SMTP_USERNAME/MAIL_USERNAME": settings.username,
            "SMTP_PASSWORD/MAIL_PASSWORD": settings.password,
            "MAIL_FROM": settings.mail_from,
            "MAIL_TO/to_email": to_email,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thiếu cấu hình gửi mail: {', '.join(missing)}")

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject
    if settings.mail_cc:
        message["Cc"] = ", ".join(settings.mail_cc)
    html = render_appraisal_email(mail_data)
    message.set_content("Email này cần trình đọc HTML để xem bảng thông tin hồ sơ.")
    message.add_alternative(html, subtype="html")
    recipients = [to_email, *settings.mail_cc]

    await aiosmtplib.send(
        message,
        recipients=recipients,
        hostname=settings.host,
        port=settings.port,
        username=settings.username,
        password=settings.password,
        start_tls=True,
        timeout=30,
    )
    return MailSendResult(to_email=to_email, subject=subject, cc_emails=settings.mail_cc)
