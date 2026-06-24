import asyncio
import sys
from pathlib import Path
from src.sqlite_store import get_case
from src.web_automation import run_company_web_entry

async def test():
    db_path = Path("data/cases.db")
    case = get_case(db_path, 1337)
    if not case:
        print("Case 1337 not found")
        return
        
    try:
        res = await run_company_web_entry(case, web_url="")
        print("Success:", res.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8'))
    except Exception as e:
        print("Exception caught in script:")
        print(str(e).encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8'))

if __name__ == "__main__":
    asyncio.run(test())
