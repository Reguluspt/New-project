import docx
import sys

sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\Truon\OneDrive\Desktop\Nháp\Form phát hành Tổ Chức.docx"
doc = docx.Document(path)
table = doc.tables[0]

def get_cell_color(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.xpath('w:shd')
    if shd:
        color = shd[0].get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill')
        return color
    return None

print("=== Cell background colors ===")
for r_idx, row in enumerate(table.rows):
    colors = [get_cell_color(cell) for cell in row.cells]
    print(f"Row {r_idx}: {colors}")
