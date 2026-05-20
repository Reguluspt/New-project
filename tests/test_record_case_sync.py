from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.record_case_sync import sync_record_rows_to_cases
from src.sqlite_store import create_case, get_case, init_db


def _record(record_id: str, contract_number: str, *, customer_info: str = "Khach hang") -> dict[str, str]:
    return {
        "id": record_id,
        "status": "CONFIRMED",
        "contract_number": contract_number,
        "customer_info": customer_info,
        "asset_description": "Tai san tu records",
        "source": "Nguon records",
    }


def _case_rows(db_path: Path) -> list[dict[str, object]]:
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM cases ORDER BY id").fetchall()]
    finally:
        conn.close()


class RecordCaseSyncTests(unittest.TestCase):
    def test_sync_record_reuses_existing_case_with_same_contract(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "cases.db"
            init_db(db_path)
            case_id = create_case(
                db_path,
                {
                    "contract_number": "N05-0849",
                    "customer_info": "Khach cu",
                    "asset_description": "Tai san cu",
                },
            )

            synced = sync_record_rows_to_cases([_record("77", "N05-0849", customer_info="Khach moi")], db_path)

            rows = _case_rows(db_path)

        self.assertEqual(synced, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], case_id)
        self.assertEqual(rows[0]["telegram_record_id"], "77")
        self.assertEqual(rows[0]["customer_info"], "Khach moi")

    def test_sync_second_record_with_same_contract_does_not_create_duplicate_case(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "cases.db"

            first_sync = sync_record_rows_to_cases([_record("77", "N05-0849", customer_info="Khach 1")], db_path)
            second_sync = sync_record_rows_to_cases([_record("78", "N05-0849", customer_info="Khach 2")], db_path)

            rows = _case_rows(db_path)

        self.assertEqual(first_sync, 1)
        self.assertEqual(second_sync, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["telegram_record_id"], "78")
        self.assertEqual(rows[0]["customer_info"], "Khach 2")


if __name__ == "__main__":
    unittest.main()
