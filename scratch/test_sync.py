import asyncio
from pathlib import Path
from src.record_case_sync import sync_records_to_cases

async def test_sync():
    records_db = Path("data/telegram_records.db")
    cases_db = Path("data/cases.db")
    count = await sync_records_to_cases(records_db, cases_db)
    print(f"Synced {count} records")

if __name__ == "__main__":
    asyncio.run(test_sync())
