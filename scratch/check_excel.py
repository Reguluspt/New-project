
import openpyxl
import sys

# Set stdout to utf-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def check_excel(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet = wb.active
    print(f"Sheet Name: {sheet.title}")
    for i, row in enumerate(sheet.iter_rows(max_row=50, values_only=True)):
        if any(row):
            print(f"Row {i+1}: {row}")

if __name__ == "__main__":
    check_excel(sys.argv[1])
