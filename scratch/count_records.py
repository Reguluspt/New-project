import sqlite3
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM records")
    count = cursor.fetchone()[0]
    print(f"Total records in telegram_records.db: {count}")
    conn.close()
