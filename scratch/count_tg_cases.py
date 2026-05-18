import sqlite3
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM cases")
        count = cursor.fetchone()[0]
        print(f"Total rows in telegram_records.db (cases table): {count}")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
