from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import numpy as np
import streamlit as st
from PIL import Image, ImageOps


def pdf_page_count(path: str | Path) -> int:
    with fitz.open(Path(path)) as doc:
        return len(doc)


@st.cache_data(max_entries=80, show_spinner=False)
def pdf_page_png(path: str | Path, page_number: int = 1, scale: float = 1.4, rotation: int = 0) -> bytes:
    target = Path(path)
    with fitz.open(target) as doc:
        page_index = max(0, min(int(page_number) - 1, len(doc) - 1))
        page = doc[page_index]
        matrix = fitz.Matrix(float(scale), float(scale)).prerotate(int(rotation))
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")


def pdf_first_page_png(path: str | Path, scale: float = 1.4) -> bytes:
    return pdf_page_png(path, page_number=1, scale=scale)


def _normalize_rotation(value: Any) -> int:
    try:
        angle = int(round(float(value)))
    except (TypeError, ValueError):
        angle = 0
    return angle % 360


def _orientation_value_from_page_api(page) -> int | None:
    orientation_getter = getattr(page, "get_text_orientation", None)
    if orientation_getter is None:
        return None

    raw_orientation = orientation_getter()
    if isinstance(raw_orientation, dict):
        for key in ("rotation", "angle", "orientation"):
            if key in raw_orientation:
                return _normalize_rotation(raw_orientation[key])
        return None
    if isinstance(raw_orientation, (list, tuple)) and raw_orientation:
        return _normalize_rotation(raw_orientation[0])
    return _normalize_rotation(raw_orientation)


def _orientation_from_text_dict(page) -> int:
    try:
        text_dict = page.get_text("dict")
    except Exception:
        return 0

    scores: dict[int, int] = {0: 0, 90: 0, 180: 0, 270: 0}
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            direction = line.get("dir")
            if not direction or len(direction) < 2:
                continue
            dx, dy = float(direction[0]), float(direction[1])
            if abs(dx) >= abs(dy):
                angle = 0 if dx >= 0 else 180
            else:
                angle = 90 if dy < 0 else 270
            line_text = "".join(span.get("text", "") for span in line.get("spans", []))
            scores[angle] += max(len(line_text.strip()), 1)
    return max(scores.items(), key=lambda item: item[1])[0]


def _scanned_page_rotation(page) -> int:
    pix = page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False)
    image = Image.open(BytesIO(pix.tobytes("png")))
    return detect_text_rotation(image)


def detect_orientation(page) -> dict[str, int | bool]:
    text = page.get_text().strip()
    is_scanned = len(text) < 10

    # PDF có text thật dùng metadata gốc; PDF scan dùng heuristic ảnh để hỗ trợ các file bị xoay lẫn lộn.
    rotation = _scanned_page_rotation(page) if is_scanned else page.rotation

    return {
        "rotation": _normalize_rotation(rotation),
        "is_scanned": is_scanned,
        "text_length": len(text),
    }


@st.cache_data(max_entries=20, show_spinner=False)
def get_pdf_metadata(path: str | Path) -> dict[str, object]:
    target = Path(path)
    pages: dict[int, dict[str, int | bool]] = {}
    with fitz.open(target) as doc:
        for page_index, page in enumerate(doc, start=1):
            pages[page_index] = detect_orientation(page)
        return {
            "path": str(target),
            "page_count": len(doc),
            "pages": pages,
        }


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
            return int(detect_orientation(page)["rotation"])

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
