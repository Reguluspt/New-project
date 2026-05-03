from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.gemini_extractor import extract_land_certificate_with_gemini, gemini_response_json_schema
from src.models import ExtractedValue, LandCertificateExtraction


def _value(value: str = "") -> ExtractedValue:
    return ExtractedValue(value=value, confidence=0.0, evidence="")


def _extraction() -> LandCertificateExtraction:
    return LandCertificateExtraction(
        so_thua_dat=_value("1"),
        so_to_ban_do=_value("2"),
        dia_chi_thua_dat=_value("Dia chi"),
        ten_chu_so_huu_cuoi_cung=_value("Chu so huu"),
        dia_chi_chu_so_huu_cuoi_cung=_value("Dia chi chu"),
        so_cccd_chu_so_huu_cuoi_cung=_value(""),
        notes=[],
        page_metadata=[],
    )


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


class GeminiExtractorTests(unittest.TestCase):
    def test_response_json_schema_does_not_include_additional_properties(self) -> None:
        schema = gemini_response_json_schema()

        self.assertFalse(_contains_key(schema, "additionalProperties"))
        self.assertEqual(schema["properties"]["page_metadata"]["type"], "array")

    def test_extract_uses_response_json_schema_instead_of_pydantic_response_schema(self) -> None:
        extraction = _extraction()
        response = Mock(parsed=extraction, text=extraction.model_dump_json())
        client = Mock()
        client.models.generate_content.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "gcn.pdf"
            file_path.write_bytes(b"%PDF-1.4\nsample")
            with patch("src.gemini_extractor.genai.Client", return_value=client):
                result = extract_land_certificate_with_gemini(
                    file_path,
                    api_key="secret",
                    model="gemini-test",
                )

        self.assertIs(result, extraction)
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertIsNone(config.response_schema)
        self.assertIsInstance(config.response_json_schema, dict)
        self.assertFalse(_contains_key(config.response_json_schema, "additionalProperties"))


if __name__ == "__main__":
    unittest.main()
