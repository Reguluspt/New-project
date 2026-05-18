import sqlite3
import os
import sys

# Set output encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def main():
    dbs = [
        r"c:\Users\Truon\Documents\New project\data\cases.db",
        r"c:\Users\Truon\Documents\New project\data\telegram_records.db"
    ]
    query = "BIDV Nam Gia Lai"
    search = f"%{query.lower()}%"
    
    for db_path in dbs:
        print(f"\nChecking {db_path}...")
        if not os.path.exists(db_path):
            print("File not found.")
            continue
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check Organizations
        cursor = conn.execute(
            "SELECT * FROM organizations WHERE LOWER(name) LIKE ? OR LOWER(abbreviation) LIKE ? OR LOWER(tax_code) LIKE ?",
            (search, search, search)
        )
        orgs = [dict(row) for row in cursor.fetchall()]
        print(f"Organizations found: {len(orgs)}")
        for org in orgs:
            print(f"  ID: {org['id']}, Name: {org['name']}, Abbr: {org.get('abbreviation')}, Tax: {org.get('tax_code')}")

        # Check Cases
        cursor = conn.execute(
            "SELECT * FROM cases WHERE customer_info LIKE ? OR tax_code LIKE ? ORDER BY id DESC LIMIT 5",
            (search, search)
        )
        cases = [dict(row) for row in cursor.fetchall()]
        print(f"Cases found: {len(cases)}")
        for case in cases:
            print(f"  ID: {case['id']}, Customer: {case['customer_info']}, Tax: {case.get('tax_code')}")
            
        conn.close()

if __name__ == "__main__":
    main()
