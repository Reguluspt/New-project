import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

async def main():
    load_dotenv("API.env")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")
    print(f"Setting webhook to: {webhook_url}")
    bot = Bot(token)
    success = await bot.set_webhook(url=webhook_url)
    print(f"Success: {success}")
    info = await bot.get_webhook_info()
    print(f"Webhook info: {info}")

if __name__ == "__main__":
    asyncio.run(main())
