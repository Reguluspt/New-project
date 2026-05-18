import sqlite3
from pathlib import Path

db_path = Path("data/cases.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT id, telegram_record_id FROM cases")
    rows = cursor.fetchall()
    
    with_id = 0
    without_id = 0
    for row in rows:
        if row[1]:
            with_id += 1
        else:
            without_id += 1
            
    print(f"Total: {len(rows)}")
    print(f"Linked to Telegram: {with_id}")
    print(f"Manually created: {without_id}")
    conn.close()
