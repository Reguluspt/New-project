import asyncio
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
        print("Success:", res)
    except Exception as e:
        print("Exception caught in script:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
