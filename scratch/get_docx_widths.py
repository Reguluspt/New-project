import docx
import sys

sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\Truon\OneDrive\Desktop\Nháp\Form phát hành Tổ Chức.docx"
doc = docx.Document(path)
table = doc.tables[0]

print("=== Cell Widths (in inches or cm if defined) ===")
for r_idx, row in enumerate(table.rows):
    widths = [cell.width.inches for cell in row.cells]
    print(f"Row {r_idx}: {widths}")
