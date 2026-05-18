import sqlite3
from pathlib import Path

db_path = Path("data/telegram_records.db")
if not db_path.exists():
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM records")
    rows = cursor.fetchall()
    
    status_counts = {}
    syncable_fields = ("contract_number", "asset_description", "dia_chi", "customer_info", "chu_so_huu", "citizen_id", "source")
    
    for row in rows:
        record = dict(row)
        if any(str(record.get(f) or "").strip() for f in syncable_fields):
            status = record.get("status")
            status_counts[status] = status_counts.get(status, 0) + 1
            
    print(f"Syncable status distribution: {status_counts}")
    conn.close()
