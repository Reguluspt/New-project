import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv
from pathlib import Path

async def set_webhook():
    load_dotenv(Path('API.env'))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
    if not webhook_url:
        # Lay tu ngrok neu khong co trong env
        import requests
        try:
            tunnels = requests.get("http://127.0.0.1:4040/api/tunnels").json()
            webhook_url = tunnels['tunnels'][0]['public_url'] + "/webhook/telegram"
        except:
            print("Khong lay duoc ngrok URL")
            return

    bot = Bot(token)
    success = await bot.set_webhook(url=webhook_url)
    print(f"Set webhook to {webhook_url}: {success}")

if __name__ == "__main__":
    asyncio.run(set_webhook())
