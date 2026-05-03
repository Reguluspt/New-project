from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from src.preview import detect_orientation, get_pdf_metadata, pdf_page_count


class PreviewMetadataTests(unittest.TestCase):
    def test_detect_orientation_marks_text_and_scanned_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mixed.pdf"
            doc = fitz.open()
            text_page = doc.new_page()
            text_page.insert_text((72, 72), "Day la trang co du lieu chu de kiem tra huong trang.")
            doc.new_page()
            doc.save(path)
            doc.close()

            with fitz.open(path) as reopened:
                text_orientation = detect_orientation(reopened[0])
                blank_orientation = detect_orientation(reopened[1])

        self.assertEqual(text_orientation["is_scanned"], False)
        self.assertEqual(text_orientation["rotation"], 0)
        self.assertGreaterEqual(text_orientation["text_length"], 10)
        self.assertEqual(blank_orientation["is_scanned"], True)
        self.assertIn(blank_orientation["rotation"], {0, 90, 180, 270})

    def test_get_pdf_metadata_returns_page_orientation_dictionary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metadata.pdf"
            doc = fitz.open()
            first = doc.new_page()
            first.insert_text((72, 72), "Trang thu nhat co text.")
            second = doc.new_page()
            second.insert_text((72, 72), "Trang thu hai co text.")
            doc.save(path)
            doc.close()

            metadata = get_pdf_metadata(path)
            page_count = pdf_page_count(path)

        self.assertEqual(metadata["path"], str(path))
        self.assertEqual(metadata["page_count"], 2)
        self.assertEqual(set(metadata["pages"]), {1, 2})
        self.assertEqual(metadata["pages"][1]["rotation"], 0)
        self.assertEqual(metadata["pages"][1]["is_scanned"], False)
        self.assertEqual(page_count, 2)


if __name__ == "__main__":
    unittest.main()
