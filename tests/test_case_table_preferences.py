from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.case_table_preferences import load_column_widths, save_column_widths


class CaseTablePreferencesTests(unittest.TestCase):
    def test_save_and_load_column_widths_round_trips_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "case_table_config.json"
            defaults = {"id": 0.7, "customer": 1.45}

            save_column_widths(path, {"id": 1.1, "customer": 2.0})
            widths = load_column_widths(path, defaults)

        self.assertEqual(widths, {"id": 1.1, "customer": 2.0})

    def test_load_column_widths_keeps_defaults_for_missing_or_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "case_table_config.json"
            path.write_text('{"column_widths": {"id": "bad", "customer": 9}}', encoding="utf-8")

            widths = load_column_widths(path, {"id": 0.7, "customer": 1.45, "note": 1.25})

        self.assertEqual(widths["id"], 0.7)
        self.assertEqual(widths["customer"], 2.5)
        self.assertEqual(widths["note"], 1.25)


if __name__ == "__main__":
    unittest.main()
