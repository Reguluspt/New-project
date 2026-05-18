import asyncio
import fitz
from PIL import Image, ImageDraw

def test_stitch():
    path = "data/uploads/1c3381deb56b436d998624cb27dc993f_3._CI_715018.pdf"
    doc = fitz.open(path)
    images = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    
    total_width = max(img.width for img in images)
    total_height = sum(img.height for img in images)
    
    stitched = Image.new("RGB", (total_width, total_height))
    y_offset = 0
    for img in images:
        stitched.paste(img, (0, y_offset))
        y_offset += img.height
        
    draw = ImageDraw.Draw(stitched)
    # The boxes from previous output:
    boxes = [
        [110, 268, 128, 347], # so_thua_dat
        [110, 551, 128, 583]  # so_to_ban_do
    ]
    for box in boxes:
        ymin, xmin, ymax, xmax = box
        x0 = (xmin / 1000.0) * total_width
        y0 = (ymin / 1000.0) * total_height
        x1 = (xmax / 1000.0) * total_width
        y1 = (ymax / 1000.0) * total_height
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        
    stitched.save("test_stitched.jpg", "JPEG")
    print("Saved to test_stitched.jpg")

if __name__ == "__main__":
    test_stitch()
