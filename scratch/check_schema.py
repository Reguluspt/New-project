import sqlite3
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(records)")
    for row in cursor.fetchall():
        print(row)
    conn.close()
