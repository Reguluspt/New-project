from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
PDF_SUFFIXES = {".pdf"}


def upload_batch_signature(uploaded_files: list[object] | tuple[object, ...] | None) -> str:
    if not uploaded_files:
        return ""
    parts: list[str] = []
    for uploaded_file in uploaded_files:
        name = getattr(uploaded_file, "name", "")
        size = getattr(uploaded_file, "size", 0)
        parts.append(f"{name}:{size}")
    return "|".join(parts)


def save_uploaded_file(uploaded_file: object, upload_dir: str | Path | None = None) -> Path:
    suffix = Path(getattr(uploaded_file, "name", "")).suffix.lower()
    target_dir = Path(upload_dir) if upload_dir else Path(tempfile.gettempdir())
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"gcn_{uuid.uuid4().hex}{suffix}"
    target.write_bytes(bytes(uploaded_file.getbuffer()))
    return target


def images_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> Path:
    if not image_paths:
        raise ValueError("Khong co anh de ghep PDF.")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    opened: list[Image.Image] = []
    try:
        for image_path in image_paths:
            image = Image.open(image_path)
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            elif image.mode == "L":
                image = image.convert("RGB")
            opened.append(image)
        first, rest = opened[0], opened[1:]
        first.save(output, "PDF", save_all=True, append_images=rest)
    finally:
        for image in opened:
            image.close()
    return output


def new_queue_item(
    *,
    path: str | Path,
    source_names: list[str],
    kind: str,
) -> dict[str, object]:
    return {
        "id": uuid.uuid4().hex,
        "path": str(path),
        "source_names": source_names,
        "kind": kind,
        "status": "pending",
        "message": "",
        "asset_count": 0,
        "provider_used": "",
        "model_used": "",
        "attempts": 0,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def make_queue_items(uploaded_files: list[object] | tuple[object, ...], upload_dir: str | Path | None = None) -> list[dict[str, object]]:
    pdf_items: list[dict[str, object]] = []
    image_paths: list[Path] = []
    image_names: list[str] = []

    for uploaded_file in uploaded_files:
        name = str(getattr(uploaded_file, "name", ""))
        suffix = Path(name).suffix.lower()
        saved_path = save_uploaded_file(uploaded_file, upload_dir=upload_dir)
        if suffix in PDF_SUFFIXES:
            pdf_items.append(new_queue_item(path=saved_path, source_names=[name], kind="pdf"))
        elif suffix in IMAGE_SUFFIXES:
            image_paths.append(saved_path)
            image_names.append(name)
        else:
            raise ValueError(f"Khong ho tro file: {name}")

    if image_paths:
        output_dir = Path(upload_dir) if upload_dir else Path(tempfile.gettempdir())
        merged_pdf = output_dir / f"gcn_merged_{uuid.uuid4().hex}.pdf"
        images_to_pdf(image_paths, merged_pdf)
        pdf_items.append(new_queue_item(path=merged_pdf, source_names=image_names, kind="image_pdf"))

    return pdf_items
