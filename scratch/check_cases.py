import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

def main():
    db_path = r"c:\Users\Truon\Documents\New project\data\cases.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("Last 10 cases:")
    cursor = conn.execute("SELECT id, customer_info, tax_code, customer_type FROM cases ORDER BY id DESC LIMIT 10")
    for row in cursor:
        print(f"  ID: {row['id']}, Customer: {row['customer_info']}, Tax: {row['tax_code']}, Type: {row['customer_type']}")
    
    conn.close()

if __name__ == "__main__":
    main()
