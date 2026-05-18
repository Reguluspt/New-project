import sqlite3
import os

def main():
    dbs = [
        r"c:\Users\Truon\Documents\New project\data\cases.db",
        r"c:\Users\Truon\Documents\New project\data\telegram_records.db"
    ]
    for db_path in dbs:
        print(f"Checking {db_path}...")
        if not os.path.exists(db_path):
            print("File not found.")
            continue
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        for table in tables:
            table_name = table[0]
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            cols = cursor.fetchall()
            print(f"  {table_name} columns: {[c[1] for c in cols]}")
        conn.close()

if __name__ == "__main__":
    main()
