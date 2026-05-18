import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv
from pathlib import Path

async def check():
    load_dotenv(Path('API.env'))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    bot = Bot(token)
    info = await bot.get_webhook_info()
    print(f"Webhook URL: {info.url}")
    print(f"Pending updates: {info.pending_update_count}")
    print(f"Last error: {info.last_error_message}")

if __name__ == "__main__":
    asyncio.run(check())
