from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .database_manager import delete_record, load_record_by_id, load_record_candidates, update_record_fields, update_record_status
from .contracts import short_contract_number
from .sqlite_store import (
    CANCELED_CASE_STATUS,
    DEFAULT_CASE_STATUS,
    DEFAULT_EXECUTION_MONTH,
    create_case,
    init_db,
    update_case,
    connect,
)


UNPAID_PAYMENT_STATUS = "Chưa thanh toán"
WEB_DELETED_STATUS = "CANCELLED"
DELETED_RECORD_STATUSES = {"CANCELLED", "DELETED"}


_SYNC_COLUMNS_INITIALIZED = {}

def _ensure_sync_columns(db_path: str | Path) -> None:
    path_key = str(db_path)
    if _SYNC_COLUMNS_INITIALIZED.get(path_key):
        return
        
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cases)").fetchall()}
        if "telegram_record_id" not in columns:
            conn.execute("ALTER TABLE cases ADD COLUMN telegram_record_id TEXT")
        if "telegram_record_status" not in columns:
            conn.execute("ALTER TABLE cases ADD COLUMN telegram_record_status TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cases_telegram_record_id ON cases(telegram_record_id)")
        conn.commit()
    _SYNC_COLUMNS_INITIALIZED[path_key] = True


def _case_id_for_record(conn: sqlite3.Connection, record: dict[str, str]) -> int | None:
    record_id = str(record.get("id") or "").strip()
    if record_id:
        row = conn.execute(
            "SELECT id FROM cases WHERE telegram_record_id = ? LIMIT 1",
            (record_id,),
        ).fetchone()
        if row:
            return int(row[0])

    contract_number = str(record.get("contract_number") or "").strip()
    if contract_number:
        row = conn.execute(
            """
            SELECT id
            FROM cases
            WHERE telegram_record_id IS NULL
              AND TRIM(COALESCE(contract_number, '')) = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (contract_number,),
        ).fetchone()
        if row:
            return int(row[0])
        row = conn.execute(
            """
            SELECT id
            FROM cases
            WHERE TRIM(COALESCE(contract_number, '')) = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (contract_number,),
        ).fetchone()
        if row:
            return int(row[0])
        record_short_contract = short_contract_number(contract_number, fallback=contract_number)
        if record_short_contract and record_short_contract != contract_number:
            for candidate in conn.execute(
                """
                SELECT id, contract_number
                FROM cases
                WHERE TRIM(COALESCE(contract_number, '')) <> ''
                ORDER BY id DESC
                """
            ).fetchall():
                candidate_contract = str(candidate["contract_number"] or "").strip()
                if short_contract_number(candidate_contract, fallback=candidate_contract) == record_short_contract:
                    return int(candidate["id"])
    return None


def _has_syncable_content(record: dict[str, str]) -> bool:
    return any(
        str(record.get(field) or "").strip()
        for field in (
            "contract_number",
            "asset_description",
            "dia_chi",
            "customer_info",
            "chu_so_huu",
            "citizen_id",
            "source",
        )
    )


def _is_deleted_record(record: dict[str, str]) -> bool:
    return str(record.get("status") or "").strip().upper() in DELETED_RECORD_STATUSES


def record_to_case_values(record: dict[str, str]) -> dict[str, Any]:
    status = str(record.get("status") or "").strip()
    customer_info = str(record.get("customer_info") or record.get("chu_so_huu") or "").strip()
    owner_name = str(record.get("chu_so_huu") or customer_info).strip()
    return {
        "customer_type": str(record.get("customer_type") or "individual").strip() or "individual",
        "case_status": CANCELED_CASE_STATUS if status == "CANCELLED" else DEFAULT_CASE_STATUS,
        "execution_month": DEFAULT_EXECUTION_MONTH,
        "payment_status": UNPAID_PAYMENT_STATUS,
        "contract_number": str(record.get("contract_number") or "").strip(),
        "asset_type": str(record.get("asset_type") or "").strip(),
        "asset_description": str(record.get("asset_description") or record.get("dia_chi") or "").strip(),
        "preliminary_status": str(record.get("preliminary_status") or "").strip(),
        "expected_finish_date": str(record.get("expected_finish_date") or "").strip(),
        "valuation_purpose": str(record.get("valuation_purpose") or "").strip(),
        "source": str(record.get("source") or "").strip(),
        "customer_info": customer_info,
        "customer_address": str(record.get("customer_address") or "").strip(),
        "citizen_id": str(record.get("citizen_id") or "").strip(),
        "valuation_fee_number": str(record.get("valuation_fee_number") or "").strip(),
        "advance_payment": str(record.get("advance_payment") or "").strip(),
        "survey_cost": str(record.get("survey_cost") or "").strip(),
        "valuation_staff": str(record.get("valuation_staff") or "").strip(),
        "personal_note": str(record.get("personal_note") or "").strip(),
        "so_thua_dat": str(record.get("so_thua") or "").strip(),
        "so_to_ban_do": str(record.get("so_to") or "").strip(),
        "dia_chi_thua_dat": str(record.get("dia_chi") or "").strip(),
        "owner_name": owner_name,
        "original_file_path": str(record.get("file_path") or "").strip(),
        "tax_code": str(record.get("tax_code") or "").strip(),
        "representative_name": str(record.get("representative_name") or "").strip(),
        "representative_position": str(record.get("representative_position") or "").strip(),
        "authorization_note": str(record.get("authorization_note") or "").strip(),
        "handover_contact_name": str(record.get("handover_contact_name") or "").strip(),
        "handover_contact_position": str(record.get("handover_contact_position") or "").strip(),
        "handover_contact_phone": str(record.get("handover_contact_phone") or "").strip(),
    }


def case_to_record_values(case: dict[str, Any]) -> dict[str, str]:
    return {
        "customer_type": str(case.get("customer_type") or "individual").strip() or "individual",
        "contract_number": str(case.get("contract_number") or "").strip(),
        "asset_type": str(case.get("asset_type") or "").strip(),
        "asset_description": str(case.get("asset_description") or "").strip(),
        "preliminary_status": str(case.get("preliminary_status") or "").strip(),
        "expected_finish_date": str(case.get("expected_finish_date") or "").strip(),
        "valuation_purpose": str(case.get("valuation_purpose") or "").strip(),
        "source": str(case.get("source") or "").strip(),
        "customer_info": str(case.get("customer_info") or "").strip(),
        "customer_address": str(case.get("customer_address") or "").strip(),
        "citizen_id": str(case.get("citizen_id") or "").strip(),
        "valuation_fee_number": str(case.get("valuation_fee_number") or "").strip(),
        "advance_payment": str(case.get("advance_payment") or "").strip(),
        "survey_cost": str(case.get("survey_cost") or "").strip(),
        "valuation_staff": str(case.get("valuation_staff") or "").strip(),
        "personal_note": str(case.get("personal_note") or "").strip(),
        "so_thua": str(case.get("so_thua_dat") or "").strip(),
        "so_to": str(case.get("so_to_ban_do") or "").strip(),
        "dia_chi": str(case.get("dia_chi_thua_dat") or "").strip(),
        "chu_so_huu": str(case.get("owner_name") or case.get("customer_info") or "").strip(),
        "tax_code": str(case.get("tax_code") or "").strip(),
        "representative_name": str(case.get("representative_name") or "").strip(),
        "representative_position": str(case.get("representative_position") or "").strip(),
        "authorization_note": str(case.get("authorization_note") or "").strip(),
        "handover_contact_name": str(case.get("handover_contact_name") or "").strip(),
        "handover_contact_position": str(case.get("handover_contact_position") or "").strip(),
        "handover_contact_phone": str(case.get("handover_contact_phone") or "").strip(),
    }


def create_case_in_conn(conn: sqlite3.Connection, values: dict[str, Any], record_id: str, record_status: str) -> int:
    from .sqlite_store import _normalize_case, CASE_FIELDS
    now = datetime.now().isoformat(timespec="seconds")
    data = _normalize_case(values)
    columns = ["created_at", "updated_at", "telegram_record_id", "telegram_record_status", *CASE_FIELDS]
    params = {
        "created_at": now,
        "updated_at": now,
        "telegram_record_id": record_id,
        "telegram_record_status": record_status,
        **data
    }
    placeholders = ", ".join(f":{column}" for column in columns)
    cursor = conn.execute(
        f"INSERT INTO cases ({', '.join(columns)}) VALUES ({placeholders})",
        params,
    )
    return int(cursor.lastrowid)


def update_case_in_conn(conn: sqlite3.Connection, case_id: int, values: dict[str, Any], record_id: str, record_status: str) -> None:
    from .sqlite_store import _normalize_case, CASE_FIELDS
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise ValueError(f"Khong tim thay ho so id={case_id}")
    existing = dict(row)
    
    merged = {field: existing.get(field, "") for field in CASE_FIELDS}
    merged.update(values)
    data = _normalize_case(merged)
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    data["id"] = case_id
    data["telegram_record_id"] = record_id
    data["telegram_record_status"] = record_status
    
    assignments = ", ".join(f"{field} = :{field}" for field in [*CASE_FIELDS, "updated_at", "telegram_record_id", "telegram_record_status"])
    cursor = conn.execute(f"UPDATE cases SET {assignments} WHERE id = :id", data)
    if cursor.rowcount == 0:
        raise ValueError(f"Khong tim thay ho so id={case_id}")


def sync_record_rows_to_cases(records: list[dict[str, str]], cases_db_path: str | Path) -> int:
    _ensure_sync_columns(cases_db_path)
    synced = 0
    for record in records:
        if _is_deleted_record(record):
            continue
        if not _has_syncable_content(record):
            continue
        record_id = str(record.get("id") or "").strip()
        if not record_id:
            continue
        
        case_values = record_to_case_values(record)
        record_status = str(record.get("status") or "").strip()
        
        try:
            with connect(cases_db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                case_id = _case_id_for_record(conn, record)

                if case_id is None:
                    create_case_in_conn(conn, case_values, record_id, record_status)
                else:
                    update_case_in_conn(conn, case_id, case_values, record_id, record_status)
            synced += 1
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                try:
                    with connect(cases_db_path) as conn:
                        conn.execute("BEGIN IMMEDIATE")
                        case_id = _case_id_for_record(conn, record)
                        if case_id is not None:
                            update_case_in_conn(conn, case_id, case_values, record_id, record_status)
                            synced += 1
                except Exception:
                    pass
            else:
                raise
    return synced


async def sync_records_to_cases(records_db_path: str | Path, cases_db_path: str | Path, *, limit: int = 1000) -> int:
    records = await load_record_candidates(records_db_path, limit=limit)
    return await asyncio.to_thread(sync_record_rows_to_cases, records, cases_db_path)


async def sync_record_to_case(records_db_path: str | Path, cases_db_path: str | Path, record_id: int | str) -> int:
    record = await load_record_by_id(records_db_path, record_id)
    if record is None or _is_deleted_record(record):
        return 0
    return await asyncio.to_thread(sync_record_rows_to_cases, [record], cases_db_path)


def _telegram_record_id_for_case(cases_db_path: str | Path, case_id: int | str) -> str:
    _ensure_sync_columns(cases_db_path)
    with sqlite3.connect(cases_db_path) as conn:
        row = conn.execute(
            "SELECT telegram_record_id FROM cases WHERE id = ? LIMIT 1",
            (int(case_id),),
        ).fetchone()
    return str(row[0] or "").strip() if row else ""


def _case_for_record_sync(cases_db_path: str | Path, case_id: int | str) -> tuple[str, dict[str, Any] | None]:
    _ensure_sync_columns(cases_db_path)
    with sqlite3.connect(cases_db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM cases WHERE id = ? LIMIT 1", (int(case_id),)).fetchone()
    if row is None:
        return "", None
    case = dict(row)
    return str(case.get("telegram_record_id") or "").strip(), case


async def sync_case_to_record(records_db_path: str | Path, cases_db_path: str | Path, case_id: int | str) -> bool:
    record_id, case = await asyncio.to_thread(_case_for_record_sync, cases_db_path, case_id)
    if not record_id or case is None:
        return False
    await update_record_fields(records_db_path, record_id, case_to_record_values(case))
    record_status = WEB_DELETED_STATUS if case.get("case_status") == CANCELED_CASE_STATUS else "CONFIRMED"
    await update_record_status(records_db_path, record_id, record_status)
    return True


async def sync_case_status_to_record(
    records_db_path: str | Path,
    cases_db_path: str | Path,
    case_id: int | str,
    *,
    case_status: str,
) -> bool:
    record_id = await asyncio.to_thread(_telegram_record_id_for_case, cases_db_path, case_id)
    if not record_id:
        return False
    record_status = WEB_DELETED_STATUS if case_status == CANCELED_CASE_STATUS else "CONFIRMED"
    await update_record_status(records_db_path, record_id, record_status)
    return True


async def sync_case_delete_to_record(records_db_path: str | Path, cases_db_path: str | Path, case_id: int | str) -> bool:
    record_id = await asyncio.to_thread(_telegram_record_id_for_case, cases_db_path, case_id)
    if not record_id:
        return False
    await delete_record(records_db_path, record_id)
    return True
