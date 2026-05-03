import asyncio
import sqlite3
import sys
import logging
import io

# Force UTF-8 for stdout/stderr
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.database_manager import get_db_path
from src.web_automation import run_company_web_entry

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    db_path = get_db_path()
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    record = db.execute("SELECT * FROM records ORDER BY id DESC LIMIT 1").fetchone()
    
    if not record:
        print("No record found in database.")
        return

    record_dict = dict(record)
    print(f"Testing with record ID: {record_dict.get('id')}")
    
    try:
        # Default internal_web_url is taken from settings in run_company_web_entry
        result = await run_company_web_entry(record_dict, web_url="")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
