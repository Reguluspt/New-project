from __future__ import annotations

from pathlib import Path

from src.database_manager import PROJECT_ROOT, resolve_records_db_path


def test_relative_records_database_path_is_project_relative() -> None:
    assert resolve_records_db_path("data/telegram_records.db") == str(
        (PROJECT_ROOT / "data" / "telegram_records.db").resolve()
    )
