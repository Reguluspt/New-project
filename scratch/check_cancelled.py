import sqlite3
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT id, status, created_at, updated_at FROM records WHERE status = 'CANCELLED' ORDER BY updated_at DESC LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row['id']}, Status: {row['status']}, Created: {row['created_at']}, Updated: {row['updated_at']}")
    conn.close()
