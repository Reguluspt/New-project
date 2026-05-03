from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import email
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.utils import formataddr, getaddresses, parseaddr
from pathlib import Path
from typing import Any, Mapping

import aioimaplib
import aiosmtplib
import aiosqlite
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from telegram import Bot

from .contracts import short_contract_number
from .mail_renderer import mail_data_from_record, render_appraisal_email
from .mail_service import GmailSmtpSettings, _parse_email_list, load_gmail_smtp_settings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_RECORDS_DB = PROJECT_ROOT / "data" / "telegram_records.db"
DEFAULT_STATE_PATH = DATA_DIR / "mail_listener_state.json"
DEFAULT_PID_PATH = DATA_DIR / "mail_listener.pid"
DEFAULT_LOG_PATH = LOG_DIR / "mail_listener_events.jsonl"
READY_FOR_WEB_STATUS = "Sẵn sàng nhập web"
AUTO_REPLY_CC = "hostktpro@gmail.com"
MATCH_THRESHOLD = 0.8


class EmailMatchExtraction(BaseModel):
    contract_id: str = Field(default="")
    customer_name: str = Field(default="")
    asset_address: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


@dataclass(frozen=True)
class IncomingEmail:
    uid: str
    subject: str
    from_email: str
    reply_to: str
    message_id: str
    references: str
    text: str
    raw: bytes


@dataclass(frozen=True)
class RecordMatch:
    record: dict[str, str]
    score: float
    reason: str


@dataclass(frozen=True)
class MailListenerSettings:
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    mailbox: str
    records_db_path: str
    gemini_api_key: str
    gemini_model: str
    telegram_bot_token: str
    telegram_chat_id: str
    auto_reply_cc: list[str]
    subject_filter: str = ""


def _load_env() -> None:
    load_dotenv(PROJECT_ROOT / "API.env")
    load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_listener_log(event: str, **fields: object) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"time": _utc_now_iso(), "event": event, **fields}
    with DEFAULT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def _read_listener_state() -> dict[str, Any]:
    if not DEFAULT_STATE_PATH.exists():
        return {"enabled": True}
    try:
        data = json.loads(DEFAULT_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"enabled": True}
    return data if isinstance(data, dict) else {"enabled": True}


def is_listener_enabled() -> bool:
    return bool(_read_listener_state().get("enabled", True))


def set_listener_enabled(enabled: bool, *, updated_by: str = "system") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_STATE_PATH.write_text(
        json.dumps(
            {
                "enabled": enabled,
                "updated_by": updated_by,
                "updated_at": _utc_now_iso(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    append_listener_log("enabled" if enabled else "disabled", updated_by=updated_by)


def write_listener_pid(pid: int | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_PID_PATH.write_text(str(pid or os.getpid()), encoding="utf-8")


def read_listener_pid() -> int | None:
    try:
        value = DEFAULT_PID_PATH.read_text(encoding="utf-8").strip()
        return int(value) if value else None
    except (OSError, ValueError):
        return None


def is_process_running(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            process = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
            if not process:
                return False
            try:
                return ctypes.windll.kernel32.WaitForSingleObject(process, 0) == 0x00000102
            finally:
                ctypes.windll.kernel32.CloseHandle(process)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def listener_status_summary() -> dict[str, object]:
    pid = read_listener_pid()
    return {
        "enabled": is_listener_enabled(),
        "pid": pid,
        "running": is_process_running(pid),
        "log_path": str(DEFAULT_LOG_PATH),
    }


def read_recent_listener_logs(limit: int = 10) -> list[dict[str, Any]]:
    if limit <= 0 or not DEFAULT_LOG_PATH.exists():
        return []
    lines = DEFAULT_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    logs: list[dict[str, Any]] = []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            item = {"event": "raw", "message": line}
        if isinstance(item, dict):
            logs.append(item)
    return logs


async def ensure_processed_email_table(db_path: str | Path) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mailbox TEXT NOT NULL,
                uid TEXT NOT NULL,
                message_id TEXT NOT NULL,
                subject TEXT,
                from_email TEXT,
                result TEXT NOT NULL,
                record_id TEXT,
                score REAL,
                processed_at TEXT NOT NULL,
                UNIQUE(mailbox, uid),
                UNIQUE(message_id)
            )
            """
        )
        await db.commit()


def _email_history_key(incoming: IncomingEmail) -> str:
    return incoming.message_id.strip() or f"{incoming.uid}:{incoming.subject}:{incoming.from_email}"


async def was_email_processed(db_path: str | Path, incoming: IncomingEmail, *, mailbox: str) -> bool:
    await ensure_processed_email_table(db_path)
    message_id = _email_history_key(incoming)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM processed_emails
            WHERE message_id = ?
               OR (mailbox = ? AND uid = ?)
            LIMIT 1
            """,
            (message_id, mailbox, incoming.uid),
        )
        row = await cursor.fetchone()
    return row is not None


async def mark_email_processed(
    db_path: str | Path,
    incoming: IncomingEmail,
    *,
    mailbox: str,
    result: str,
    record_id: str | None = None,
    score: float | None = None,
) -> None:
    await ensure_processed_email_table(db_path)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO processed_emails (
                mailbox, uid, message_id, subject, from_email,
                result, record_id, score, processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                result = excluded.result,
                record_id = excluded.record_id,
                score = excluded.score,
                processed_at = excluded.processed_at
            """,
            (
                mailbox,
                incoming.uid,
                _email_history_key(incoming),
                incoming.subject,
                incoming.from_email,
                result,
                record_id,
                score,
                _utc_now_iso(),
            ),
        )
        await db.commit()


def load_mail_listener_settings() -> MailListenerSettings:
    _load_env()
    username = os.getenv("IMAP_USERNAME", os.getenv("MAIL_USERNAME", "")).strip()
    password = os.getenv("IMAP_PASSWORD", os.getenv("MAIL_PASSWORD", "")).strip()
    cc_values = _parse_email_list(os.getenv("MAIL_LISTENER_CC", AUTO_REPLY_CC))
    if AUTO_REPLY_CC not in {item.lower() for item in cc_values}:
        cc_values.append(AUTO_REPLY_CC)
    return MailListenerSettings(
        imap_host=os.getenv("IMAP_HOST", "imap.gmail.com").strip() or "imap.gmail.com",
        imap_port=_int_env("IMAP_PORT", 993),
        imap_username=username,
        imap_password=password,
        mailbox=os.getenv("IMAP_MAILBOX", "INBOX").strip() or "INBOX",
        records_db_path=os.getenv("TELEGRAM_RECORDS_DB", str(DEFAULT_RECORDS_DB)).strip() or str(DEFAULT_RECORDS_DB),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        auto_reply_cc=cc_values,
        subject_filter=os.getenv("MAIL_LISTENER_SUBJECT_FILTER", "").strip(),
    )


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not payload:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _decode_header_value(value: object) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    try:
        decoded = str(make_header(decode_header(raw)))
    except Exception:
        decoded = raw
    return re.sub(r"[\r\n]+", " ", decoded).strip()


def parse_incoming_email(raw: bytes, *, uid: str = "") -> IncomingEmail:
    message = email.message_from_bytes(raw)
    text_parts: list[str] = []
    html_parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            disposition = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            content_type = part.get_content_type()
            if content_type == "text/plain":
                text_parts.append(_decode_part(part))
            elif content_type == "text/html":
                html_parts.append(_decode_part(part))
    else:
        if message.get_content_type() == "text/html":
            html_parts.append(_decode_part(message))
        else:
            text_parts.append(_decode_part(message))

    text = "\n".join(part.strip() for part in text_parts if part.strip())
    if not text and html_parts:
        text = strip_html("\n".join(html_parts))

    from_header = str(message.get("From") or "")
    reply_to_header = str(message.get("Reply-To") or "")
    from_email = parseaddr(from_header)[1]
    reply_to = parseaddr(reply_to_header)[1] or from_email
    return IncomingEmail(
        uid=uid,
        subject=_decode_header_value(message.get("Subject")),
        from_email=from_email,
        reply_to=reply_to,
        message_id=_decode_header_value(message.get("Message-ID")),
        references=_decode_header_value(message.get("References")),
        text=text,
        raw=raw,
    )


def strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", without_tags).strip()


def _schema_without_additional_properties(schema: Any) -> Any:
    if isinstance(schema, dict):
        return {
            key: _schema_without_additional_properties(value)
            for key, value in schema.items()
            if key != "additionalProperties"
        }
    if isinstance(schema, list):
        return [_schema_without_additional_properties(item) for item in schema]
    return schema


def analyze_email_with_gemini(email_text: str, *, api_key: str, model: str) -> EmailMatchExtraction:
    if not api_key:
        raise RuntimeError("Thiếu GEMINI_API_KEY để phân tích email.")
    client = genai.Client(api_key=api_key)
    schema = _schema_without_additional_properties(EmailMatchExtraction.model_json_schema())
    response = client.models.generate_content(
        model=model,
        contents=[
            (
                "Hãy đọc email yêu cầu định giá và trích xuất JSON gồm: "
                "contract_id nếu có, customer_name, asset_address và confidence từ 0 đến 1.\n\n"
                f"Nội dung email:\n{email_text}"
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0,
        ),
    )
    if isinstance(response.parsed, EmailMatchExtraction):
        return response.parsed
    if isinstance(response.parsed, dict):
        return EmailMatchExtraction.model_validate(response.parsed)
    return EmailMatchExtraction.model_validate_json(response.text)


def _normalize(value: object) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _token_score(query: str, value: str) -> float:
    query_tokens = {token for token in _normalize(query).split() if len(token) >= 3}
    value_tokens = {token for token in _normalize(value).split() if len(token) >= 3}
    if not query_tokens or not value_tokens:
        return 0.0
    return len(query_tokens & value_tokens) / len(query_tokens)


def match_record(candidates: list[Mapping[str, Any]], extraction: EmailMatchExtraction) -> RecordMatch | None:
    best: RecordMatch | None = None
    short_contract = short_contract_number(extraction.contract_id)
    for candidate in candidates:
        record = {str(key): str(value or "") for key, value in candidate.items()}
        contract_number = record.get("contract_number", "")
        score = 0.0
        reason = ""
        if short_contract and short_contract_number(contract_number) == short_contract:
            score = 1.0
            reason = "contract_id"
        else:
            customer_score = _token_score(extraction.customer_name, record.get("customer_info") or record.get("chu_so_huu"))
            address_score = max(
                _token_score(extraction.asset_address, record.get("asset_description")),
                _token_score(extraction.asset_address, record.get("dia_chi")),
            )
            score = max(customer_score, address_score) * float(extraction.confidence or 0)
            reason = "customer/address"
        if best is None or score > best.score:
            best = RecordMatch(record=record, score=score, reason=reason)
    return best


def _contract_id_for_update(contract_id: str) -> str:
    value = (contract_id or "").strip()
    short_value = short_contract_number(value)
    if re.search(r"\bN\d{2}[-.]\d+\b", short_value, flags=re.IGNORECASE):
        return value
    return ""


async def load_record_candidates(db_path: str | Path) -> list[dict[str, str]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM records
            ORDER BY id DESC
            LIMIT 500
            """
        )
        rows = await cursor.fetchall()
    return [{key: str(row[key] or "") for key in row.keys()} for row in rows]


async def update_matched_record(db_path: str | Path, record_id: int, contract_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE records
            SET contract_number = COALESCE(NULLIF(?, ''), contract_number),
                status = ?
            WHERE id = ?
            """,
            (contract_id, READY_FOR_WEB_STATUS, record_id),
        )
        await db.commit()


def _reply_subject(subject: str) -> str:
    clean_subject = re.sub(r"[\r\n]+", " ", subject or "").strip()
    return clean_subject if clean_subject.lower().startswith("re:") else f"Re: {clean_subject or 'Thông tin hồ sơ'}"


def _reply_recipients(incoming: IncomingEmail, extra_cc: list[str]) -> tuple[str, list[str]]:
    to_email = incoming.reply_to or incoming.from_email
    cc = []
    seen = {to_email.lower()}
    for item in extra_cc:
        email_address = parseaddr(item)[1] or item
        if email_address and email_address.lower() not in seen:
            seen.add(email_address.lower())
            cc.append(email_address)
    return to_email, cc


def build_reply_message(
    *,
    incoming: IncomingEmail,
    record: Mapping[str, Any],
    smtp_settings: GmailSmtpSettings,
    cc_list: list[str],
) -> EmailMessage:
    to_email, cc = _reply_recipients(incoming, cc_list)
    mail_data = mail_data_from_record(dict(record)).model_copy(update={"greeting_name": "Sơn"})
    html = render_appraisal_email(mail_data)
    message = EmailMessage()
    message["From"] = smtp_settings.mail_from
    message["To"] = to_email
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = _reply_subject(incoming.subject)
    if incoming.message_id:
        message["In-Reply-To"] = incoming.message_id
        message["References"] = f"{incoming.references} {incoming.message_id}".strip()
    message.set_content("Email này cần trình đọc HTML để xem bảng thông tin hồ sơ.")
    message.add_alternative(html, subtype="html")
    return message


async def send_thread_reply(
    *,
    incoming: IncomingEmail,
    record: Mapping[str, Any],
    smtp_settings: GmailSmtpSettings,
    cc_list: list[str],
) -> None:
    message = build_reply_message(
        incoming=incoming,
        record=record,
        smtp_settings=smtp_settings,
        cc_list=cc_list,
    )
    recipients = [email_address for _name, email_address in getaddresses([message.get("To", ""), message.get("Cc", "")]) if email_address]
    await aiosmtplib.send(
        message,
        recipients=recipients,
        hostname=smtp_settings.host,
        port=smtp_settings.port,
        username=smtp_settings.username,
        password=smtp_settings.password,
        start_tls=True,
        timeout=30,
    )


async def notify_telegram(settings: MailListenerSettings, text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    bot = Bot(settings.telegram_bot_token)
    await bot.send_message(chat_id=settings.telegram_chat_id, text=text)


async def process_incoming_email(raw: bytes, *, uid: str, settings: MailListenerSettings) -> RecordMatch | None:
    incoming = parse_incoming_email(raw, uid=uid)
    try:
        extraction = analyze_email_with_gemini(
            incoming.text,
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
        candidates = await load_record_candidates(settings.records_db_path)
        match = match_record(candidates, extraction)
        if match is None or match.score <= MATCH_THRESHOLD:
            append_listener_log(
                "skipped",
                uid=uid,
                subject=incoming.subject,
                from_email=incoming.from_email,
                reason="no_match" if match is None else "low_score",
                score=round(match.score, 3) if match is not None else None,
                extracted_contract=extraction.contract_id,
                customer_name=extraction.customer_name,
            )
            return match

        append_listener_log(
            "matched",
            uid=uid,
            subject=incoming.subject,
            from_email=incoming.from_email,
            record_id=match.record.get("id"),
            score=round(match.score, 3),
            reason=match.reason,
            extracted_contract=extraction.contract_id,
        )
        smtp_settings = load_gmail_smtp_settings()
        await send_thread_reply(
            incoming=incoming,
            record=match.record,
            smtp_settings=smtp_settings,
            cc_list=settings.auto_reply_cc,
        )
        await update_matched_record(
            settings.records_db_path,
            int(match.record["id"]),
            _contract_id_for_update(extraction.contract_id) or match.record.get("contract_number", ""),
        )
        append_listener_log(
            "replied",
            uid=uid,
            subject=incoming.subject,
            record_id=match.record.get("id"),
            status=READY_FOR_WEB_STATUS,
        )
        await notify_telegram(
            settings,
            (
                "AI đã đối soát và phản hồi tự động.\n"
                f"Hồ sơ: #{match.record.get('id')} - {short_contract_number(extraction.contract_id or match.record.get('contract_number'))}\n"
                f"Độ tin cậy: {int(match.score * 100)}%\n"
                f"Trạng thái: {READY_FOR_WEB_STATUS}"
            ),
        )
        return match
    except Exception as exc:
        append_listener_log(
            "failed",
            uid=uid,
            subject=incoming.subject,
            from_email=incoming.from_email,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


async def _fetch_message_by_uid(client: aioimaplib.IMAP4_SSL, uid: str) -> bytes | None:
    _status, data = await client.uid("FETCH", uid, "(RFC822)")
    for item in data:
        if isinstance(item, (bytes, bytearray)) and b"\r\n" in item:
            return bytes(item)
    return None


def _extract_imap_ids(data: list[object]) -> list[str]:
    joined = b" ".join(item for item in data if isinstance(item, (bytes, bytearray))).decode(errors="replace")
    return re.findall(r"\b\d+\b", joined)


async def poll_unseen_once(settings: MailListenerSettings) -> int:
    client = aioimaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    await client.wait_hello_from_server()
    await client.login(settings.imap_username, settings.imap_password)
    await client.select(settings.mailbox)
    processed = 0
    try:
        _status, data = await client.uid_search("UNSEEN")
        for uid in _extract_imap_ids(data):
            raw = await _fetch_message_by_uid(client, uid)
            if raw is None:
                continue
            incoming = parse_incoming_email(raw, uid=uid)
            if await was_email_processed(settings.records_db_path, incoming, mailbox=settings.mailbox):
                append_listener_log(
                    "skipped",
                    uid=uid,
                    subject=incoming.subject,
                    from_email=incoming.from_email,
                    reason="duplicate",
                )
                continue
            if settings.subject_filter:
                haystack = f"{incoming.subject}\n{incoming.text}".casefold()
                if settings.subject_filter.casefold() not in haystack:
                    append_listener_log(
                        "skipped",
                        uid=uid,
                        subject=incoming.subject,
                        from_email=incoming.from_email,
                        reason="subject_filter",
                        filter=settings.subject_filter,
                    )
                    continue
            match = await process_incoming_email(raw, uid=uid, settings=settings)
            result = "replied" if match is not None and match.score > MATCH_THRESHOLD else "skipped"
            await mark_email_processed(
                settings.records_db_path,
                incoming,
                mailbox=settings.mailbox,
                result=result,
                record_id=match.record.get("id") if match is not None else None,
                score=round(match.score, 3) if match is not None else None,
            )
            processed += 1
    finally:
        await client.logout()
    return processed


async def listen_forever(settings: MailListenerSettings | None = None, *, poll_interval_seconds: int = 60) -> None:
    current_settings = settings or load_mail_listener_settings()
    append_listener_log("started", pid=os.getpid(), mailbox=current_settings.mailbox)
    while True:
        if is_listener_enabled():
            try:
                await poll_unseen_once(current_settings)
            except Exception as exc:
                append_listener_log("failed", scope="poll", error_type=type(exc).__name__, error=str(exc))
        else:
            append_listener_log("skipped", reason="listener_disabled")
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    write_listener_pid()
    try:
        asyncio.run(listen_forever())
    finally:
        append_listener_log("stopped", pid=os.getpid())
