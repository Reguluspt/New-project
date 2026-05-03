from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

from .models import LandCertificateExtraction


EXTRACTION_INSTRUCTIONS = """
Ban la tro ly trich xuat du lieu tu Giay chung nhan quyen su dung dat cua Viet Nam.
Chi trich xuat thong tin nhin thay trong file, khong suy dien thong tin khong co.

Can lay cac truong:
- So thua dat.
- So to ban do.
- Dia chi thua dat.
- Ten chu so huu/cu nguoi su dung dat cuoi cung.
- Dia chi cua chu so huu cuoi cung.
- So can cuoc cong dan/CMND cua chu so huu cuoi cung.

Quy tac nghiep vu:
- Neu GCN co muc bien dong/chuyen nhuong, chon chu so huu gan nhat/cuoi cung theo thu tu ghi tren tai lieu.
- Neu khong co bien dong, lay nguoi su dung dat/chu so huu tren trang chinh.
- Neu co nhieu dong chu so huu, giu nguyen day du ten cac ca nhan/to chuc.
- Neu khong thay CCCD/CMND hoac dia chi, de value rong va ghi ly do trong notes.
- Evidence phai ngan gon, chi can mot cum tu/dong lien quan de nguoi dung kiem tra.
- Neu co the xac dinh huong trang, tra ve page_metadata la danh sach object.
- Moi object gom page_number va rotation. rotation chi duoc la 0, 90, 180 hoac 270.
""".strip()


def _to_data_url(path: Path) -> tuple[str, str]:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return mime_type, f"data:{mime_type};base64,{encoded}"


def _content_for_file(path: Path) -> dict[str, str]:
    mime_type, data_url = _to_data_url(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return {
            "type": "input_file",
            "filename": path.name,
            "file_data": data_url,
        }

    if mime_type.startswith("image/"):
        return {
            "type": "input_image",
            "image_url": data_url,
            "detail": "high",
        }

    raise ValueError("Chi ho tro file PDF hoac anh PNG/JPG/JPEG/WebP.")


def extract_land_certificate(
    file_path: str | Path,
    *,
    api_key: str,
    model: str,
) -> LandCertificateExtraction:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    client = OpenAI(api_key=api_key)
    response = client.responses.parse(
        model=model,
        instructions=EXTRACTION_INSTRUCTIONS,
        input=[
            {
                "role": "user",
                "content": [
                    _content_for_file(path),
                    {
                        "type": "input_text",
                        "text": (
                            "Hay doc file GCN nay va tra ve dung schema. "
                            "Tap trung vao so thua, so to ban do, dia chi thua dat, "
                            "chu so huu cuoi cung, dia chi va CCCD/CMND cua nguoi do."
                        ),
                    },
                ],
            }
        ],
        text_format=LandCertificateExtraction,
        temperature=0,
        store=False,
    )
    return response.output_parsed
