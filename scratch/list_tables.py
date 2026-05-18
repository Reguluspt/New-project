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
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        print(f"Database {db_name} has tables: {', '.join(tables)}")
    except Exception as e:
        print(f"Error checking {db_name}: {e}")
    conn.close()
