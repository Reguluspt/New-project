from __future__ import annotations

import mimetypes
from copy import deepcopy
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .extractor import EXTRACTION_INSTRUCTIONS
from .models import LandCertificateExtraction


def _part_for_file(path: Path) -> types.Part:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        mime_type = "application/pdf"
    if not (mime_type.startswith("image/") or mime_type == "application/pdf"):
        raise ValueError("Chi ho tro file PDF hoac anh PNG/JPG/JPEG/WebP.")
    return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)


def _remove_unsupported_schema_keys(schema: Any) -> Any:
    if isinstance(schema, dict):
        cleaned: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "additionalProperties":
                continue
            cleaned[key] = _remove_unsupported_schema_keys(value)
        return cleaned
    if isinstance(schema, list):
        return [_remove_unsupported_schema_keys(item) for item in schema]
    return schema


def gemini_response_json_schema() -> dict[str, Any]:
    """Return a Gemini-compatible JSON schema without SDK-added extras."""
    schema = deepcopy(LandCertificateExtraction.model_json_schema())
    return _remove_unsupported_schema_keys(schema)


def extract_land_certificate_with_gemini(
    file_path: str | Path,
    *,
    api_key: str,
    model: str,
) -> LandCertificateExtraction:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            _part_for_file(path),
            (
                "Hay doc file GCN nay va tra ve dung schema. "
                "Tap trung vao so thua, so to ban do, dia chi thua dat, "
                "chu so huu cuoi cung, dia chi va CCCD/CMND cua nguoi do."
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=EXTRACTION_INSTRUCTIONS,
            response_mime_type="application/json",
            response_json_schema=gemini_response_json_schema(),
            temperature=0,
        ),
    )

    if isinstance(response.parsed, LandCertificateExtraction):
        return response.parsed
    if isinstance(response.parsed, dict):
        return LandCertificateExtraction.model_validate(response.parsed)
    return LandCertificateExtraction.model_validate_json(response.text)
