from __future__ import annotations

from io import BytesIO
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageOps


def pdf_page_count(path: str | Path) -> int:
    doc = fitz.open(Path(path))
    return len(doc)


def pdf_page_png(path: str | Path, page_number: int = 1, scale: float = 1.4, rotation: int = 0) -> bytes:
    doc = fitz.open(Path(path))
    page_index = max(0, min(page_number - 1, len(doc) - 1))
    page = doc[page_index]
    matrix = fitz.Matrix(scale, scale).prerotate(rotation)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


def pdf_first_page_png(path: str | Path, scale: float = 1.4) -> bytes:
    return pdf_page_png(path, page_number=1, scale=scale)


def _projection_score(image: Image.Image) -> tuple[float, float]:
    grayscale = image.convert("L")
    grayscale = ImageOps.autocontrast(grayscale)
    grayscale.thumbnail((900, 900))
    array = np.asarray(grayscale, dtype=np.uint8)
    threshold = max(80, min(230, int(np.percentile(array, 45))))
    dark = array < threshold
    if dark.mean() < 0.002:
        dark = array < min(245, int(np.percentile(array, 25)) + 20)
    row_sums = dark.sum(axis=1).astype(np.float32)
    col_sums = dark.sum(axis=0).astype(np.float32)
    if row_sums.size == 0 or col_sums.size == 0:
        return 0.0, 0.0
    main_score = float(row_sums.std() - col_sums.std() * 0.22)
    midpoint = max(1, row_sums.size // 2)
    top_score = float(row_sums[:midpoint].sum())
    bottom_score = float(row_sums[midpoint:].sum())
    return main_score, top_score - bottom_score


def detect_text_rotation(image: Image.Image) -> int:
    candidates: list[tuple[float, int]] = []
    for rotation in (0, 90, 180, 270):
        rotated = image.rotate(-rotation, expand=True) if rotation else image
        score, _balance = _projection_score(rotated)
        candidates.append((score, rotation))
    best_score = max(score for score, _rotation in candidates)
    tied = [rotation for score, rotation in candidates if abs(score - best_score) < 0.01]

    # Projection-based orientation can reliably detect whether text lines are
    # horizontal or vertical, but it cannot reliably distinguish 0 from 180 on
    # scanned documents without OCR. Prefer the non-flipped orientation on ties
    # so an already-upright page is not turned upside down.
    for preferred in (0, 90, 270, 180):
        if preferred in tied:
            return preferred
    return max(candidates)[1]


def detect_text_rotation_for_path(path: str | Path, page_number: int = 1) -> int:
    target = Path(path)
    if target.suffix.lower() == ".pdf":
        with fitz.open(target) as doc:
            page_index = max(0, min(page_number - 1, len(doc) - 1))
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png")))
        return detect_text_rotation(image)

    image = ImageOps.exif_transpose(Image.open(target))
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")
    return detect_text_rotation(image)


def normalize_image_for_preview(path: str | Path, rotation: int = 0, scale: float = 1.0) -> bytes:
    image = Image.open(path)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")
    if rotation:
        image = image.rotate(-rotation, expand=True)
    if scale and scale != 1.0:
        new_size = (
            max(1, int(image.width * scale)),
            max(1, int(image.height * scale)),
        )
        image = image.resize(new_size)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def crop_png_bytes(
    png_bytes: bytes,
    *,
    left_pct: int,
    top_pct: int,
    right_pct: int,
    bottom_pct: int,
) -> bytes:
    image = Image.open(BytesIO(png_bytes))
    width, height = image.size
    left = int(width * left_pct / 100)
    top = int(height * top_pct / 100)
    right = int(width * right_pct / 100)
    bottom = int(height * bottom_pct / 100)
    if right <= left:
        right = min(width, left + 1)
    if bottom <= top:
        bottom = min(height, top + 1)
    cropped = image.crop((left, top, right, bottom))
    output = BytesIO()
    cropped.save(output, format="PNG")
    return output.getvalue()


def pdf_thumbnail_png(path: str | Path, page_number: int = 1, rotation: int = 0) -> bytes:
    return pdf_page_png(path, page_number=page_number, scale=0.35, rotation=rotation)
