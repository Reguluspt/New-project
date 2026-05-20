from __future__ import annotations

import unittest
from unittest.mock import patch

from src.models import ExtractedValue, LandCertificateExtraction
from src.ocr_accumulator import apply_multi_extraction_to_form


def _value(value: str) -> ExtractedValue:
    return ExtractedValue(value=value, confidence=0.95, evidence="test")


def _asset() -> LandCertificateExtraction:
    return LandCertificateExtraction(
        so_thua_dat=_value("65"),
        so_to_ban_do=_value("KQH"),
        dia_chi_thua_dat=_value("Xa Dien Phu"),
        ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
        dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
        so_cccd_chu_so_huu_cuoi_cung=_value(""),
        notes=[],
        page_metadata=[],
    )


class OcrAccumulatorTests(unittest.TestCase):
    def test_applying_same_asset_from_two_files_keeps_two_form_lines(self) -> None:
        state: dict[str, object] = {}
        with patch("src.ocr_accumulator.st.session_state", state):
            first_count = apply_multi_extraction_to_form(_asset(), append=True)
            second_count = apply_multi_extraction_to_form(_asset(), append=True)

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)
        asset_lines = str(state["entry_asset_description"]).splitlines()
        so_thua_lines = str(state["entry_so_thua"]).splitlines()
        self.assertEqual(len(asset_lines), 2)
        self.assertEqual(len(so_thua_lines), 2)
        self.assertEqual(asset_lines[0], asset_lines[1])


if __name__ == "__main__":
    unittest.main()
