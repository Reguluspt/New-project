import sqlite3
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT status, COUNT(*) FROM records GROUP BY status")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Status: {row[0]}, Count: {row[1]}")
    conn.close()
