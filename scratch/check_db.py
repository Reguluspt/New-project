
import sqlite3
import sys

def check_db(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cases)")
    columns = cursor.fetchall()
    print(f"Table: cases")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_db(sys.argv[1])
