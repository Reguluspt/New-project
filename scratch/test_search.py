import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, re

conn = sqlite3.connect('data/telegram_records.db')

tests = ['vcb dũng', 'bidv khôi', 'seabank', 'gia lai danh', 'BIDV, nGÂN', 'vcb']

for q in tests:
    keywords = [kw for kw in re.split(r'[,\s]+', q.strip().lower()) if kw]
    conditions = " AND ".join("LOWER(short_name) LIKE ?" for _ in keywords)
    params = tuple(f"%{kw}%" for kw in keywords)
    rows = conn.execute(
        f"SELECT id, short_name FROM delivery_contacts WHERE {conditions}", params
    ).fetchall()
    names = [r[1] for r in rows]
    print(f"  [{q}] -> {len(names)} results: {names[:3]}{'...' if len(names) > 3 else ''}")

conn.close()
