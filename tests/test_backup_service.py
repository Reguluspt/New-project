from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.backup_service import create_backup


class BackupServiceTests(unittest.TestCase):
    def test_create_backup_zips_essential_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "cases.db").write_text("db content")
            (data_dir / "ai_config.json").write_text("{}")
            
            backup_path = create_backup(data_dir)
            
            self.assertIsNotNone(backup_path)
            self.assertTrue(backup_path.exists())
            self.assertEqual(backup_path.suffix, ".zip")
            self.assertIn("backup_", backup_path.name)
            
            # Check cleanup
            for i in range(12):
                create_backup(data_dir, max_backups=5)
            
            backups = list((data_dir / "backups").glob("backup_*.zip"))
            self.assertEqual(len(backups), 5)

    def test_create_backup_returns_none_if_no_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            backup_path = create_backup(data_dir)
            self.assertIsNone(backup_path)


if __name__ == "__main__":
    unittest.main()
