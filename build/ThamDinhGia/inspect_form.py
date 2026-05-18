import asyncio
import sqlite3
import sys
import logging
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.database_manager import get_db_path
from src.web_automation import load_web_automation_settings, start_browser_and_login
from playwright.async_api import async_playwright

async def main():
    settings = load_web_automation_settings()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await start_browser_and_login(context)
        
        html = await page.evaluate("""() => {
            const labelNode = Array.from(document.querySelectorAll("label"))
                .find((node) => node.textContent.includes("Có bao gồm phí khảo sát"));
            if (labelNode && labelNode.parentElement) {
                return labelNode.parentElement.innerHTML;
            }
            return "Not found";
        }""")
        print("Có bao gồm phí khảo sát HTML:")
        print(html)

        html2 = await page.evaluate("""() => {
            const labelNode = Array.from(document.querySelectorAll("label"))
                .find((node) => node.textContent.includes("Thẩm định giá"));
            if (labelNode && labelNode.parentElement) {
                return labelNode.parentElement.innerHTML;
            }
            return "Not found";
        }""")
        print("Thẩm định giá HTML:")
        print(html2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
