from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.email_utils import format_recipient_info

# Load HTML template
template_path = Path("src/templates/phathanh_template.html")
html_content = template_path.read_text(encoding="utf-8")

# Let's test the single-line recipient format without newlines
recipient_raw = "CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - VP TẠI GIA LAI Địa chỉ: 90/60/3 Trường Chinh, phường Pleiku, tỉnh Gia Lai Điện thoại 0905226968"

# Apply the automatic formatting rule!
recipient_clean = format_recipient_info(recipient_raw)
recipient_html = recipient_clean.replace("\n", "<br>")

# Apply the bolding rules
if "Địa chỉ:" in recipient_html:
    recipient_html = recipient_html.replace("Địa chỉ:", "<strong>Địa chỉ:</strong>")
elif "Địa chỉ" in recipient_html:
    recipient_html = recipient_html.replace("Địa chỉ", "<strong>Địa chỉ</strong>")
    
if "Điện thoại:" in recipient_html:
    recipient_html = recipient_html.replace("Điện thoại:", "<strong>Điện thoại:</strong>")
elif "Điện thoại" in recipient_html:
    recipient_html = recipient_html.replace("Điện thoại", "<strong>Điện thoại</strong>")

replacements = {
    "{{ customer_name }}": "CÔNG TY TNHH MTV KHOÁNG SẢN SXK",
    "{{ customer_address }}": "45C Phan Đình Phùng, Phường Pleiku, Tỉnh Gia Lai.",
    "{{ customer_extra_html }}": "", # Organization doesn't have individual CCCD
    "{{ recipient_info }}": recipient_html,
    "{{ date_receive }}": "18/05/2026",
    "{{ date_payment }}": "17/05/2026",
    "{{ personal_note }}": "", # In the notes cell, do not pre-fill any content!
    "cid:logo_cenvalue": "logo.jpg" # Map CID to local relative file path for rendering in browser
}

rendered_html = html_content
for placeholder, value in replacements.items():
    rendered_html = rendered_html.replace(placeholder, str(value))

# Write to preview file
output_path = Path("src/templates/preview_phathanh.html")
output_path.write_text(rendered_html, encoding="utf-8")
print("Preview HTML generated successfully with blank notes and formatted contacts.")
