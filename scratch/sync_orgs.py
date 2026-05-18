import sqlite3
import os
from pathlib import Path

source_db = Path("data/cases.db")
target_db = Path("data/telegram_records.db")

if not source_db.exists():
    print(f"Source DB {source_db} not found")
    exit(1)

s_conn = sqlite3.connect(source_db)
t_conn = sqlite3.connect(target_db)

try:
    # Ensure target table exists
    t_conn.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tax_code TEXT,
            name TEXT NOT NULL,
            abbreviation TEXT,
            address TEXT,
            representative TEXT,
            position TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Get source data
    cursor = s_conn.execute("SELECT tax_code, name, abbreviation, address, representative, position FROM organizations")
    rows = cursor.fetchall()
    
    # Insert into target
    count = 0
    for row in rows:
        # Check if already exists by name
        exists = t_conn.execute("SELECT 1 FROM organizations WHERE name = ?", (row[1],)).fetchone()
        if not exists:
            t_conn.execute("""
                INSERT INTO organizations (tax_code, name, abbreviation, address, representative, position)
                VALUES (?, ?, ?, ?, ?, ?)
            """, row)
            count += 1
    
    t_conn.commit()
    print(f"Synced {count} organizations to {target_db}")

except Exception as e:
    print(f"Error: {e}")
finally:
    s_conn.close()
    t_conn.close()
