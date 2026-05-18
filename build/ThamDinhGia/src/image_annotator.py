from __future__ import annotations

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import fitz  # PyMuPDF

from .models import LandCertificateMultiExtraction

def _get_boxes_from_extraction(extraction: LandCertificateMultiExtraction) -> list[list[int]]:
    boxes = []
    for asset in getattr(extraction, "assets", []):
        for field_name in [
            "so_thua_dat", "so_to_ban_do", "dia_chi_thua_dat",
            "ten_chu_so_huu_cuoi_cung", "dia_chi_chu_so_huu_cuoi_cung", "so_cccd_chu_so_huu_cuoi_cung"
        ]:
            field_obj = getattr(asset, field_name, None)
            if field_obj and getattr(field_obj, "value", "").strip() and getattr(field_obj, "bounding_box", None):
                box = field_obj.bounding_box
                if isinstance(box, list) and len(box) >= 5:
                    boxes.append(box[:5])
    return boxes

def annotate_document_with_bounding_boxes(
    file_path: str | Path,
    extraction: LandCertificateMultiExtraction,
    output_dir: str | Path,
) -> str | None:
    boxes = _get_boxes_from_extraction(extraction)
    if not boxes:
        return None

    path = Path(file_path)
    if not path.exists():
        return None

    os.makedirs(output_dir, exist_ok=True)
    out_filename = f"annotated_{path.stem}.jpg"
    out_path = os.path.join(output_dir, out_filename)

    try:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            doc = fitz.open(str(path))
            images = []
            for i in range(doc.page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=150)
                images.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
            doc.close()

            if not images:
                return None

            total_height = sum(img.height for img in images)
            
            # Identify which pages contain bounding boxes
            pages_to_keep = set()
            for box in boxes:
                page_idx = box[0]
                if 0 <= page_idx < len(images):
                    pages_to_keep.add(page_idx)

            if not pages_to_keep:
                pages_to_keep.add(0) # Fallback to first page
                
            # Keep only pages that have boxes
            kept_images = [images[i] for i in sorted(pages_to_keep)]
            
            total_width = max(img.width for img in kept_images)
            kept_total_height = sum(img.height for img in kept_images)
            
            img = Image.new("RGB", (total_width, kept_total_height))
            y_offset = 0
            page_y_starts = {} # Map original page index to new Y offset
            
            for i in sorted(pages_to_keep):
                page_y_starts[i] = y_offset
                img.paste(images[i], (0, y_offset))
                y_offset += images[i].height
                
            # Update drawing logic to draw on the new stitched image
            draw = ImageDraw.Draw(img)
            for box in boxes:
                page_idx, ymin, xmin, ymax, xmax = box
                if ymin > ymax:
                    ymin, ymax = ymax, ymin
                if xmin > xmax:
                    xmin, xmax = xmax, xmin
                    
                if page_idx in page_y_starts and 0 <= page_idx < len(images):
                    pimg = images[page_idx]
                    
                    x0 = (xmin / 1000.0) * pimg.width
                    x1 = (xmax / 1000.0) * pimg.width
                    
                    y0 = page_y_starts[page_idx] + (ymin / 1000.0) * pimg.height
                    y1 = page_y_starts[page_idx] + (ymax / 1000.0) * pimg.height
                    
                    draw.rectangle([x0, y0, x1, y1], outline="red", width=5)
                    
        else:
            img = Image.open(str(path))
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")

            width, height = img.size
            draw = ImageDraw.Draw(img)

            for box in boxes:
                _, ymin, xmin, ymax, xmax = box
                if ymin > ymax:
                    ymin, ymax = ymax, ymin
                if xmin > xmax:
                    xmin, xmax = xmax, xmin
                    
                x0 = (xmin / 1000.0) * width
                y0 = (ymin / 1000.0) * height
                x1 = (xmax / 1000.0) * width
                y1 = (ymax / 1000.0) * height
                
                draw.rectangle([x0, y0, x1, y1], outline="red", width=5)

        if img.height > 4000 or img.width > 4000:
            img.thumbnail((4000, 4000), Image.Resampling.LANCZOS)

        img.save(out_path, "JPEG", quality=85)
        return out_path

    except Exception as e:
        print(f"Error annotating image: {e}")
        return None
