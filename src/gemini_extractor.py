from __future__ import annotations

import mimetypes
from copy import deepcopy
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .extractor import EXTRACTION_INSTRUCTIONS
from .models import LandCertificateExtraction, LandCertificateMultiExtraction


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
    schema = deepcopy(LandCertificateMultiExtraction.model_json_schema())
    return _remove_unsupported_schema_keys(schema)


def extract_land_certificate_with_gemini(
    file_path: str | Path,
    *,
    api_key: str,
    model: str,
) -> LandCertificateMultiExtraction:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            _part_for_file(path),
            (
                "Hay dem va trich xuat tat ca tai san/GCN co trong tai lieu, khong chi lay tai san dau tien. "
                "Neu mot file co nhieu thua dat hoac nhieu GCN, moi tai san la mot phan tu trong assets. "
                "Tap trung vao so thua, so to ban do, dia chi thua dat, chu so huu cuoi cung, dia chi va CCCD/CMND cua nguoi do."
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=EXTRACTION_INSTRUCTIONS,
            response_mime_type="application/json",
            response_json_schema=gemini_response_json_schema(),
            temperature=0,
        ),
    )

    if isinstance(response.parsed, LandCertificateMultiExtraction):
        return response.parsed
    if isinstance(response.parsed, LandCertificateExtraction):
        return LandCertificateMultiExtraction(assets=[response.parsed])
    if isinstance(response.parsed, dict):
        if "assets" in response.parsed:
            return LandCertificateMultiExtraction.model_validate(response.parsed)
        return LandCertificateMultiExtraction(assets=[LandCertificateExtraction.model_validate(response.parsed)])
    return LandCertificateMultiExtraction.model_validate_json(response.text)


def organization_gemini_response_json_schema() -> dict[str, Any]:
    from .models import OrganizationExtraction
    schema = deepcopy(OrganizationExtraction.model_json_schema())
    return _remove_unsupported_schema_keys(schema)


def extract_organization_from_contract_with_gemini(
    file_path: str | Path,
    *,
    api_key: str,
    model: str,
) -> Any:
    from .models import OrganizationExtraction
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    client = genai.Client(api_key=api_key)
    
    contents = []
    if path.suffix.lower() == ".docx":
        try:
            import docx
            doc = docx.Document(path)
            text = "\n".join([para.text for para in doc.paragraphs])
            contents.append(text)
        except Exception as e:
            raise ValueError(f"Lỗi khi đọc file .docx: {e}")
    else:
        contents.append(_part_for_file(path))

    contents.append(
        "Hãy đọc file hợp đồng này và trích xuất thông tin của tổ chức (công ty, doanh nghiệp, ngân hàng...) "
        "đóng vai trò là Bên A hoặc Bên B trong hợp đồng. Ưu tiên bên là khách hàng hoặc đối tác của công ty thẩm định giá. "
        "Cần tìm Mã số thuế (nếu có), Tên đầy đủ, Địa chỉ trụ sở chính, và Người đại diện pháp luật cùng Chức vụ của họ."
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=organization_gemini_response_json_schema(),
            temperature=0,
        ),
    )

    if isinstance(response.parsed, OrganizationExtraction):
        return response.parsed
    if isinstance(response.parsed, dict):
        return OrganizationExtraction.model_validate(response.parsed)
    return OrganizationExtraction.model_validate_json(response.text)
