import os
from fastapi.testclient import TestClient
from src.telegram_server import app
from dotenv import load_dotenv
from pathlib import Path

def test_zalo_webhook_with_secret():
    # Load env
    env_path = Path("API.env")
    if env_path.exists():
        load_dotenv(env_path)
    
    secret = os.getenv("ZALO_WEBHOOK_SECRET", "").strip()
    print(f"Su dung Secret Token: {secret}")
    
    client = TestClient(app)
    
    # Giả lập payload từ Zalo Bot Creator
    payload = {
        "ok": True,
        "result": {
            "message": {
                "from": { "id": "test_user_123", "display_name": "Nguoi dung Test" },
                "chat": { "id": "test_chat_123", "chat_type": "PRIVATE" },
                "text": "Lenh kiem tra he thong",
                "message_id": "msg_999",
                "date": 1750000000
            },
            "event_name": "message.text.received"
        }
    }
    
    headers = {
        "X-Bot-Api-Secret-Token": secret
    }
    
    print("Dang gui gia lap Webhook den /webhook/zalo...")
    response = client.post("/webhook/zalo", json=payload, headers=headers)
    
    print(f"HTTP Status: {response.status_code}")
    print(f"Response Body: {response.json()}")
    
    if response.status_code == 200 and response.json().get("ok") is True:
        print("--- KET QUA: WEBHOOK HOAT DONG TOT ---")
    else:
        print("--- KET QUA: CO LOI XAY RA ---")

if __name__ == "__main__":
    test_zalo_webhook_with_secret()
