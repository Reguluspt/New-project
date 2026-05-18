from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path


def create_backup(data_dir: Path, *, max_backups: int = 10) -> Path | None:
    """
    Creates a zip backup of essential database and config files.
    Cleans up old backups exceeding max_backups.
    """
    backup_dir = data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"backup_{timestamp}.zip"

    essential_files = [
        "cases.db",
        "telegram_records.db",
        "template_config.json",
        "ai_config.json",
        "case_table_config.json",
        "case_output_config.json",
    ]

    found_files = 0
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zip_handle:
        for file_name in essential_files:
            file_path = data_dir / file_name
            if file_path.is_file():
                zip_handle.write(file_path, arcname=file_name)
                found_files += 1

    if found_files == 0:
        if backup_path.exists():
            backup_path.unlink()
        return None

    # Cleanup old backups
    backups = sorted(backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime)
    while len(backups) > max_backups:
        oldest = backups.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass

    return backup_path
