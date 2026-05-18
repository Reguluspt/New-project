import sqlite3
from pathlib import Path

db_path = Path("data/cases.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT case_status, COUNT(*) FROM cases GROUP BY case_status")
    rows = cursor.fetchall()
    for row in rows:
        status = row[0]
        count = row[1]
        # Print representation to avoid encoding issues
        print(f"Status (repr): {repr(status)}, Count: {count}")
    conn.close()
