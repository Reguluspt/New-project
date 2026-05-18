import sqlite3
import os
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name, abbreviation, tax_code FROM organizations LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"Name: {row[0]}, Abbr: {row[1]}, Tax: {row[2]}")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    conn.close()
