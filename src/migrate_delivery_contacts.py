
import asyncio
import openpyxl
from pathlib import Path
import os
import sys
from src.database_manager import add_delivery_contact, resolve_records_db_path, ensure_tracking_record_schema

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def migrate():
    excel_path = r"C:\Users\Truon\OneDrive\Desktop\Nháp\Danh sách chuyển phát.xlsx"
    db_path = os.getenv("RECORDS_DB_PATH", "data/telegram_records.db")
    
    await ensure_tracking_record_schema(db_path)
    
    print(f"Reading Excel: {excel_path}")
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active
    
    count = 0
    for row in sheet.iter_rows(min_row=1, values_only=True):
        if len(row) >= 6:
            short_name = row[4]
            full_details = row[5]
            
            if short_name and full_details and str(short_name).strip() and str(full_details).strip():
                # Filter rows that look like contacts
                s_name = str(short_name).strip()
                if any(x in s_name for x in ["Mr.", "Ms.", "Mrs.", "Văn phòng", "VCB", "BIDV", "SeaBank"]):
                    await add_delivery_contact(db_path, s_name, str(full_details).strip())
                    count += 1
                    # Avoid console encoding issues by not printing full name if possible, or just be careful
                    try:
                        print(f"Added: {s_name}")
                    except:
                        print(f"Added record {count}")

    print(f"Successfully migrated {count} contacts.")

if __name__ == "__main__":
    asyncio.run(migrate())
