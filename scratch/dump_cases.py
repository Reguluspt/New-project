import sqlite3
from pathlib import Path

db_path = Path("data/cases.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT id, contract_number, customer_info, telegram_record_id FROM cases")
    rows = cursor.fetchall()
    
    print(f"Total rows in cases table: {len(rows)}")
    for row in rows:
        print(f"ID: {row['id']}, HĐ: {row['contract_number']}, Customer: {row['customer_info']}, TelegramID: {row['telegram_record_id']}")
    conn.close()
