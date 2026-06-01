from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any, Mapping

import aiosqlite

from .contracts import short_contract_number
from .professional_forwarding import DEFAULT_PROFESSIONAL_RECIPIENT


SENT_TO_PROFESSIONAL_STATUS = "SENT_TO_PROFESSIONAL"
CERTIFICATE_RECEIVED_STATUS = "CERTIFICATE_RECEIVED"
READY_FOR_WEB_STATUS = "S\u1eb5n s\u00e0ng nh\u1eadp web"
DELETED_RECORD_STATUSES = {"CANCELLED", "DELETED"}


async def find_organization_by_query(db_path: str | Path, query: str) -> list[dict[str, Any]]:
    db_path = resolve_records_db_path(db_path)
    search = str(query or "").strip().casefold()
    if not search:
        return []
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM organizations
            WHERE LOWER(name) LIKE ?
               OR LOWER(abbreviation) LIKE ?
               OR LOWER(tax_code) LIKE ?
            """,
            (f"%{search}%", f"%{search}%", f"%{search}%"),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RECORDS_DB = PROJECT_ROOT / "data" / "telegram_records.db"

TRACKING_RECORD_TEXT_COLUMNS = {
    "so_thua",
    "so_to",
    "dia_chi",
    "chu_so_huu",
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
    "customer_phone",
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
    "professional_forward_enabled",
    "professional_recipient_email",
}


def resolve_records_db_path(db_path: str | Path | None = None) -> str:
    raw_path = (
        str(db_path).strip()
        if db_path is not None and str(db_path).strip()
        else os.getenv("RECORDS_DB_PATH", os.getenv("TELEGRAM_RECORDS_DB", str(DEFAULT_RECORDS_DB))).strip()
    )
    raw_path = os.path.expanduser(raw_path or str(DEFAULT_RECORDS_DB))
    if not os.path.isabs(raw_path):
        raw_path = os.path.join(str(PROJECT_ROOT), raw_path)
    return os.path.abspath(raw_path)


def get_db_path() -> str:
    """Return the single absolute SQLite path used by Telegram, mail and web chat."""
    return resolve_records_db_path()


def log_records_db_path(component: str, db_path: str | Path | None = None) -> str:
    resolved = resolve_records_db_path(db_path)
    message = f"{_now_iso()} [{component}] RECORDS_DB_PATH={resolved}"
    print(message, flush=True)
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "db_paths.log").open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    return resolved


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


async def ensure_mail_workflow_schema(db_path: str | Path) -> None:
    db_path = resolve_records_db_path(db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("PRAGMA busy_timeout = 30000")
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(records)")
        columns = {str(row[1]) for row in await cursor.fetchall()}
        additions = {
            "certificate_number": "TEXT NOT NULL DEFAULT ''",
            "outbound_message_id": "TEXT NOT NULL DEFAULT ''",
            "outbound_subject": "TEXT NOT NULL DEFAULT ''",
            "outbound_sent_at": "TEXT NOT NULL DEFAULT ''",
            "professional_sent_at": "TEXT NOT NULL DEFAULT ''",
            "professional_forward_enabled": "TEXT NOT NULL DEFAULT '1'",
            "professional_recipient_email": f"TEXT NOT NULL DEFAULT '{DEFAULT_PROFESSIONAL_RECIPIENT}'",
        }
        for column, definition in additions.items():
            if column not in columns:
                await db.execute(f"ALTER TABLE records ADD COLUMN {column} {definition}")
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_records_outbound_message_id
                ON records(outbound_message_id)
                """
            )
        await db.commit()
_TRACKING_SCHEMA_INITIALIZED = {}

async def ensure_tracking_record_schema(db_path: str | Path) -> None:
    db_path = resolve_records_db_path(db_path)
    path_key = str(db_path)
    if _TRACKING_SCHEMA_INITIALIZED.get(path_key):
        return
        
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("PRAGMA busy_timeout = 30000")
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(records)")
        columns = {str(row[1]) for row in await cursor.fetchall()}
        for column in sorted(TRACKING_RECORD_TEXT_COLUMNS):
            if column not in columns:
                default_sql = "'individual'" if column == "customer_type" else "''"
                await db.execute(f"ALTER TABLE records ADD COLUMN {column} TEXT NOT NULL DEFAULT {default_sql}")
        await db.commit()
    
    # Ensure organizations table exists
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_code TEXT,
                name TEXT NOT NULL,
                abbreviation TEXT,
                address TEXT,
                representative TEXT,
                position TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()

    await ensure_mail_workflow_schema(db_path)

    # Khởi tạo bảng danh bạ chuyển phát
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS delivery_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_name TEXT NOT NULL,
                full_details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()

    await ensure_sobo_schema(db_path)
    _TRACKING_SCHEMA_INITIALIZED[path_key] = True


async def add_delivery_contact(db_path: str | Path, short_name: str, full_details: str) -> int:
    db_path = resolve_records_db_path(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        cursor = await db.execute(
            "INSERT INTO delivery_contacts (short_name, full_details) VALUES (?, ?)",
            (short_name.strip(), full_details.strip())
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_all_delivery_contacts(db_path: str | Path) -> list[dict[str, Any]]:
    db_path = resolve_records_db_path(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM delivery_contacts ORDER BY short_name ASC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def search_delivery_contacts(db_path: str | Path, query: str) -> list[dict[str, Any]]:
    db_path = resolve_records_db_path(db_path)
    # Tách từ khóa bằng dấu phẩy hoặc khoảng trắng, lọc rỗng
    keywords = [kw for kw in re.split(r'[,\s]+', query.strip().lower()) if kw]
    if not keywords:
        return []
    # Mỗi từ khóa phải xuất hiện trong short_name (AND)
    conditions = " AND ".join("LOWER(short_name) LIKE ?" for _ in keywords)
    params = tuple(f"%{kw}%" for kw in keywords)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"SELECT * FROM delivery_contacts WHERE {conditions} ORDER BY short_name ASC",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]



def _tracking_value(values: Mapping[str, Any], field: str) -> str:
    aliases = {
        "so_thua": ("so_thua", "so_thua_dat"),
        "so_to": ("so_to", "so_to_ban_do"),
        "dia_chi": ("dia_chi", "dia_chi_thua_dat"),
        "chu_so_huu": ("chu_so_huu", "owner_name"),
        "valuation_purpose": ("valuation_purpose", "purpose"),
        "personal_note": ("personal_note", "notes"),
    }
    for key in aliases.get(field, (field,)):
        value = values.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    if field == "customer_type":
        return "individual"
    if field == "professional_forward_enabled":
        return str(values.get(field) if values.get(field) is not None else "1")
    if field == "professional_recipient_email":
        return str(values.get(field) or DEFAULT_PROFESSIONAL_RECIPIENT)
    return ""


async def create_outbound_tracking_record(
    db_path: str | Path,
    values: Mapping[str, Any],
    *,
    file_path: str = "desktop_mail",
) -> int:
    db_path = resolve_records_db_path(db_path)
    await ensure_tracking_record_schema(db_path)
    columns = ["file_path", *sorted(TRACKING_RECORD_TEXT_COLUMNS), "status"]
    payload = {
        "file_path": file_path,
        "status": str(values.get("status") or "PENDING"),
        **{field: _tracking_value(values, field) for field in TRACKING_RECORD_TEXT_COLUMNS},
    }
    placeholders = ", ".join(f":{column}" for column in columns)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        cursor = await db.execute(
            f"INSERT INTO records ({', '.join(columns)}) VALUES ({placeholders})",
            {column: payload[column] for column in columns},
        )
        await db.commit()
        return int(cursor.lastrowid)


async def create_record_from_values(
    db_path: str | Path,
    values: Mapping[str, Any],
    *,
    file_path: str,
    status: str = "PENDING",
) -> int:
    payload = {**values, "status": status}
    return await create_outbound_tracking_record(db_path, payload, file_path=file_path)


async def update_record_fields(db_path: str | Path, record_id: int | str, values: Mapping[str, Any]) -> None:
    db_path = resolve_records_db_path(db_path)
    allowed_fields = {"so_thua", "so_to", "dia_chi", "chu_so_huu", *TRACKING_RECORD_TEXT_COLUMNS}
    updates = {field: str(value or "") for field, value in values.items() if field in allowed_fields}
    if not updates:
        return
    await ensure_tracking_record_schema(db_path)
    assignments = ", ".join(f"{field} = ?" for field in updates)
    params = [*updates.values(), int(record_id)]
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(f"UPDATE records SET {assignments} WHERE id = ?", params)
        await db.commit()


async def update_record_status(db_path: str | Path, record_id: int | str, status: str) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_tracking_record_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("UPDATE records SET status = ? WHERE id = ?", (status, int(record_id)))
        await db.commit()


async def delete_record(db_path: str | Path, record_id: int | str) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_tracking_record_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("DELETE FROM records WHERE id = ?", (int(record_id),))
        await db.commit()


async def get_record(db_path: str | Path, record_id: int | str) -> dict[str, str]:
    db_path = resolve_records_db_path(db_path)
    await ensure_tracking_record_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM records
            WHERE id = ?
              AND COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
            """,
            (int(record_id),),
        )
        row = await cursor.fetchone()
    if row is None:
        raise ValueError(f"Khong tim thay ban ghi #{record_id}.")
    return {key: str(row[key] or "") for key in row.keys()}


async def get_record_by_contract_number(db_path: str | Path, contract_query: str) -> dict[str, str] | None:
    db_path = resolve_records_db_path(db_path)
    query = (contract_query or "").strip()
    if not query:
        return None
    await ensure_tracking_record_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        # Tìm kiếm theo số hợp đồng đầy đủ hoặc rút gọn
        cursor = await db.execute(
            """
            SELECT *
            FROM records
            WHERE COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
              AND (contract_number LIKE ? OR contract_number LIKE ?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (f"%{query}%", f"%{short_contract_number(query)}%")
        )
        row = await cursor.fetchone()
    if row:
        return {key: str(row[key] or "") for key in row.keys()}
    return None


async def get_case_by_contract_number(cases_db_path: str | Path, contract_query: str) -> dict[str, str] | None:
    """Tìm kiếm hồ sơ trong database của phần mềm (cases.db)"""
    query = (contract_query or "").strip()
    if not query:
        return None
    
    if not Path(cases_db_path).exists():
        return None

    async with aiosqlite.connect(cases_db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        # Tìm kiếm trong bảng cases của phần mềm
        cursor = await db.execute(
            "SELECT * FROM cases WHERE contract_number LIKE ? ORDER BY id DESC LIMIT 1",
            (f"%{query}%",)
        )
        row = await cursor.fetchone()
    
    if row:
        # Map các trường của phần mềm về format chung của bot
        data = {key: str(row[key] or "") for key in row.keys()}
        # Đảm bảo có các trường cần thiết cho phát hành
        return data
    return None
    short_query = short_contract_number(query)
    async with aiosqlite.connect(db_path, timeout=30) as db:
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


async def load_record_candidates(db_path: str | Path, *, limit: int = 500) -> list[dict[str, str]]:
    db_path = resolve_records_db_path(db_path)
    await ensure_tracking_record_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM records
            WHERE COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    return [{key: str(row[key] or "") for key in row.keys()} for row in rows]


async def update_matched_record_contract(
    db_path: str | Path,
    record_id: int | str,
    *,
    contract_id: str,
    status: str = READY_FOR_WEB_STATUS,
) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_tracking_record_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            """
            UPDATE records
            SET contract_number = COALESCE(NULLIF(?, ''), contract_number),
                status = ?
            WHERE id = ?
            """,
            (contract_id, status, int(record_id)),
        )
        await db.commit()


async def save_outbound_message(
    db_path: str | Path,
    record_id: int | str,
    *,
    message_id: str,
    subject: str,
) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_mail_workflow_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            """
            UPDATE records
            SET outbound_message_id = ?,
                outbound_subject = ?,
                outbound_sent_at = ?
            WHERE id = ?
            """,
            (message_id, subject, _now_iso(), int(record_id)),
        )
        await db.commit()


async def load_record_by_id(db_path: str | Path, record_id: int | str) -> dict[str, str] | None:
    db_path = resolve_records_db_path(db_path)
    await ensure_mail_workflow_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM records WHERE id = ?", (int(record_id),))
        row = await cursor.fetchone()
    return {key: str(row[key] or "") for key in row.keys()} if row is not None else None


def _normalize_subject(value: str) -> str:
    subject = str(value or "").strip()
    subject = re.sub(r"[\r\n\t]+", " ", subject)
    subject = re.sub(r"\s+", " ", subject).strip()
    prefix_pattern = re.compile(r"^(?:(?:re|fw|fwd|v/v)\s*:\s*)+", flags=re.IGNORECASE)
    while True:
        cleaned = prefix_pattern.sub("", subject).strip()
        if cleaned == subject:
            break
        subject = cleaned
    return re.sub(r"\s+", " ", subject).strip().casefold()


def _like_pattern(value: str) -> str:
    text = _normalize_subject(value)
    text = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{text}%"


async def find_record_by_thread_reference(
    db_path: str | Path,
    *,
    in_reply_to: str = "",
    references: str = "",
    subject: str = "",
) -> dict[str, str] | None:
    db_path = resolve_records_db_path(db_path)
    await ensure_mail_workflow_schema(db_path)
    ref_blob = f"{in_reply_to or ''} {references or ''}"
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        if ref_blob.strip():
            cursor = await db.execute(
                """
                SELECT *
                FROM records
                WHERE TRIM(outbound_message_id) <> ''
                  AND COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
                  AND INSTR(?, outbound_message_id) > 0
                ORDER BY id DESC
                LIMIT 1
                """,
                (ref_blob,),
            )
            row = await cursor.fetchone()
            if row is not None:
                return {key: str(row[key] or "") for key in row.keys()}

        normalized_subject = _normalize_subject(subject)
        if normalized_subject:
            incoming_like = _like_pattern(normalized_subject)
            cursor = await db.execute(
                """
                SELECT *
                FROM records
                WHERE TRIM(outbound_subject) <> ''
                  AND COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
                  AND (
                    LOWER(outbound_subject) LIKE ? ESCAPE '\\'
                    OR (
                        TRIM(outbound_subject) <> ''
                        AND ? LIKE '%' || LOWER(outbound_subject) || '%'
                    )
                  )
                ORDER BY id DESC
                LIMIT 1
                """,
                (incoming_like, normalized_subject),
            )
            row = await cursor.fetchone()
            if row is not None:
                return {key: str(row[key] or "") for key in row.keys()}
            cursor = await db.execute(
                """
                SELECT *
                FROM records
                WHERE TRIM(outbound_subject) <> ''
                  AND COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
                ORDER BY id DESC
                LIMIT 500
                """
            )
            rows = await cursor.fetchall()
            for row in rows:
                row_subject = _normalize_subject(str(row["outbound_subject"] or ""))
                if row_subject and (row_subject in normalized_subject or normalized_subject in row_subject):
                    return {key: str(row[key] or "") for key in row.keys()}
    return None


def _tokenize_subject(value: str) -> set[str]:
    text = _normalize_subject(value)
    return {token for token in re.split(r"\W+", text) if len(token) >= 3}


def _subject_overlap_score(subject: str, record: Mapping[str, Any]) -> float:
    subject_tokens = _tokenize_subject(subject)
    if not subject_tokens:
        return 0.0
    record_text = " ".join(
        str(record.get(key) or "")
        for key in [
            "outbound_subject",
            "asset_description",
            "dia_chi",
            "source",
            "customer_info",
            "chu_so_huu",
        ]
    )
    record_tokens = _tokenize_subject(record_text)
    if not record_tokens:
        return 0.0
    return len(subject_tokens & record_tokens) / len(subject_tokens)


async def find_recent_record_by_subject(
    db_path: str | Path,
    *,
    subject: str,
    limit: int = 50,
    min_score: float = 0.35,
    require_outbound_subject: bool = False,
) -> dict[str, str] | None:
    db_path = resolve_records_db_path(db_path)
    await ensure_mail_workflow_schema(db_path)
    normalized_subject = _normalize_subject(subject)
    like_pattern = _like_pattern(normalized_subject)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        if normalized_subject:
            outbound_clause = "TRIM(outbound_subject) <> '' AND " if require_outbound_subject else ""
            cursor = await db.execute(
                f"""
                SELECT *
                FROM records
                WHERE COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
                  AND {outbound_clause}(LOWER(COALESCE(outbound_subject, '')) LIKE ? ESCAPE '\\'
                   OR LOWER(COALESCE(asset_description, '')) LIKE ? ESCAPE '\\'
                   OR LOWER(COALESCE(dia_chi, '')) LIKE ? ESCAPE '\\'
                   OR LOWER(COALESCE(source, '')) LIKE ? ESCAPE '\\'
                   OR LOWER(COALESCE(customer_info, '')) LIKE ? ESCAPE '\\'
                   OR LOWER(COALESCE(chu_so_huu, '')) LIKE ? ESCAPE '\\'
                   OR ? LIKE '%' || LOWER(COALESCE(outbound_subject, '')) || '%')
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    like_pattern,
                    like_pattern,
                    like_pattern,
                    like_pattern,
                    like_pattern,
                    like_pattern,
                    normalized_subject,
                    limit,
                ),
            )
        else:
            cursor = await db.execute(
                """
                SELECT *
                FROM records
                WHERE COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = await cursor.fetchall()
        if not rows and normalized_subject:
            outbound_clause = "AND TRIM(outbound_subject) <> ''" if require_outbound_subject else ""
            cursor = await db.execute(
                f"""
                SELECT *
                FROM records
                WHERE COALESCE(status, '') NOT IN ('CANCELLED', 'DELETED')
                {outbound_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
    best: tuple[float, dict[str, str]] | None = None
    for row in rows:
        record = {key: str(row[key] or "") for key in row.keys()}
        if require_outbound_subject and not str(record.get("outbound_subject") or "").strip():
            continue
        score = _subject_overlap_score(subject, record)
        if best is None or score > best[0]:
            best = (score, record)
    if best is not None and best[0] >= min_score:
        return best[1]
    return None


async def update_certificate_forwarded(
    db_path: str | Path,
    record_id: int | str,
    *,
    certificate_number: str,
) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_mail_workflow_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            """
            UPDATE records
            SET certificate_number = ?,
                contract_number = ?,
                status = ?,
                professional_sent_at = ?
            WHERE id = ?
            """,
            (certificate_number, certificate_number, SENT_TO_PROFESSIONAL_STATUS, _now_iso(), int(record_id)),
        )
        await db.commit()


async def update_certificate_received(
    db_path: str | Path,
    record_id: int | str,
    *,
    certificate_number: str,
) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_mail_workflow_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            """
            UPDATE records
            SET certificate_number = ?,
                contract_number = ?,
                status = ?
            WHERE id = ?
            """,
            (certificate_number, certificate_number, CERTIFICATE_RECEIVED_STATUS, int(record_id)),
        )
        await db.commit()


def owner_name_from_record(record: Mapping[str, Any]) -> str:
    return str(
        record.get("owner_name")
        or record.get("chu_so_huu")
        or record.get("customer_info")
        or record.get("recipient_name")
        or f"#{record.get('id', '')}"
    ).strip()


async def ensure_sobo_schema(db_path: str | Path) -> None:
    db_path = resolve_records_db_path(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("PRAGMA busy_timeout = 30000")
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute(
            "CREATE TABLE IF NOT EXISTS sobo_records ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
            "  asset_type TEXT NOT NULL,"
            "  asset_sub_type TEXT,"
            "  source TEXT,"
            "  so_thua TEXT,"
            "  so_to TEXT,"
            "  dia_chi TEXT,"
            "  link TEXT,"
            "  email_recipient TEXT,"
            "  outbound_subject TEXT,"
            "  outbound_message_id TEXT,"
            "  outbound_sent_at TEXT,"
            "  responded_at TEXT,"
            "  status TEXT NOT NULL DEFAULT 'PENDING',"
            "  note TEXT,"
            "  equipment_name TEXT"
            ")"
        )
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sobo_outbound_msg_id ON sobo_records(outbound_message_id)")
        await db.commit()


async def create_sobo_record(db_path: str | Path, values: dict[str, Any]) -> int:
    db_path = resolve_records_db_path(db_path)
    await ensure_sobo_schema(db_path)
    fields = [
        "asset_type", "asset_sub_type", "source", "so_thua", "so_to", "dia_chi",
        "link", "email_recipient", "outbound_subject", "outbound_message_id",
        "outbound_sent_at", "status", "note", "equipment_name"
    ]
    columns = ", ".join(fields)
    placeholders = ", ".join(f":{f}" for f in fields)
    
    payload = {f: str(values.get(f) or "").strip() for f in fields}
    if not payload["status"]:
        payload["status"] = "PENDING"
    if not payload["outbound_sent_at"]:
        payload["outbound_sent_at"] = datetime.now().isoformat()
        
    async with aiosqlite.connect(db_path, timeout=30) as db:
        cursor = await db.execute(
            f"INSERT INTO sobo_records ({columns}) VALUES ({placeholders})",
            payload
        )
        await db.commit()
        return int(cursor.lastrowid)


async def update_sobo_record_status(db_path: str | Path, record_id: int, status: str, responded_at: str | None = None) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_sobo_schema(db_path)
    if not responded_at and status == "RESPONDED":
        responded_at = datetime.now().isoformat()
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            "UPDATE sobo_records SET status = ?, responded_at = ? WHERE id = ?",
            (status, responded_at, int(record_id))
        )
        await db.commit()


async def update_sobo_record_note(db_path: str | Path, record_id: int, note: str) -> None:
    db_path = resolve_records_db_path(db_path)
    await ensure_sobo_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute(
            "UPDATE sobo_records SET note = ? WHERE id = ?",
            (note.strip(), int(record_id))
        )
        await db.commit()


async def get_all_sobo_records(db_path: str | Path) -> list[dict[str, Any]]:
    db_path = resolve_records_db_path(db_path)
    await ensure_sobo_schema(db_path)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM sobo_records ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def find_sobo_record_by_thread(db_path: str | Path, ref_blob: str, subject: str) -> dict[str, Any] | None:
    db_path = resolve_records_db_path(db_path)
    await ensure_sobo_schema(db_path)
    ref_blob = ref_blob.strip()
    normalized_subject = _normalize_subject(subject)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Đối soát bằng message_id
        if ref_blob:
            cursor = await db.execute(
                "SELECT * FROM sobo_records "
                "WHERE outbound_message_id IS NOT NULL AND TRIM(outbound_message_id) <> '' "
                "  AND INSTR(?, outbound_message_id) > 0 "
                "ORDER BY id DESC LIMIT 1",
                (ref_blob,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
                
        # 2. Đối soát bằng tiêu đề
        if normalized_subject:
            like_pattern = _like_pattern(normalized_subject)
            cursor = await db.execute(
                "SELECT * FROM sobo_records "
                "WHERE outbound_subject IS NOT NULL AND TRIM(outbound_subject) <> '' "
                "  AND ( "
                "    LOWER(outbound_subject) LIKE ? ESCAPE '\\' "
                "    OR ? LIKE '%' || LOWER(outbound_subject) || '%' "
                "  ) "
                "ORDER BY id DESC LIMIT 1",
                (like_pattern, normalized_subject)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
                
            # Fallback đối soát bằng Python-side comparison trên 500 dòng gần nhất để hỗ trợ tiếng Việt có dấu
            cursor = await db.execute(
                "SELECT * FROM sobo_records "
                "WHERE outbound_subject IS NOT NULL AND TRIM(outbound_subject) <> '' "
                "ORDER BY id DESC LIMIT 500"
            )
            rows = await cursor.fetchall()
            for r in rows:
                row_subject = _normalize_subject(str(r["outbound_subject"] or ""))
                if row_subject and (row_subject in normalized_subject or normalized_subject in row_subject):
                    return dict(r)
                    
    return None

