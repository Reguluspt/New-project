import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv
from pathlib import Path

async def test_send():
    load_dotenv(Path('API.env'))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    bot = Bot(token)
    await bot.send_message(chat_id=chat_id, text="Bot đã khởi động lại và đang chờ lệnh của anh.")
    print("Message sent.")

if __name__ == "__main__":
    asyncio.run(test_send())
