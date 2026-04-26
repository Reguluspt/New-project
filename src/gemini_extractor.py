from __future__ import annotations

import mimetypes
from pathlib import Path

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
            response_schema=LandCertificateExtraction,
            temperature=0,
        ),
    )

    if isinstance(response.parsed, LandCertificateExtraction):
        return response.parsed
    if isinstance(response.parsed, dict):
        return LandCertificateExtraction.model_validate(response.parsed)
    return LandCertificateExtraction.model_validate_json(response.text)
