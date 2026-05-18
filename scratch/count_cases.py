import sqlite3
from pathlib import Path

db_path = Path("data/cases.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM cases")
    count = cursor.fetchone()[0]
    print(f"Total records in cases.db (cases table): {count}")
    conn.close()
