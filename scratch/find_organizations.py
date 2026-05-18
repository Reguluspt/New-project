import sqlite3
import os
from pathlib import Path

databases = ["data/telegram_records.db", "cases.db", "data/cases.db"]
for db_name in databases:
    db_path = Path(db_name)
    if not db_path.exists():
        continue
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='organizations'")
        if cursor.fetchone():
            print(f"Database {db_name} HAS organizations table")
            cursor = conn.execute("SELECT COUNT(*) FROM organizations")
            count = cursor.fetchone()[0]
            print(f"  Count: {count}")
            if count > 0:
                cursor = conn.execute("SELECT name, abbreviation FROM organizations LIMIT 3")
                for row in cursor.fetchall():
                    print(f"    - {row[0]} ({row[1]})")
        else:
            print(f"Database {db_name} does NOT have organizations table")
    except Exception as e:
        print(f"Error checking {db_name}: {e}")
    conn.close()
