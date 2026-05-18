import os
from pathlib import Path

def update_env_file(key, value):
    env_path = Path("API.env")
    lines = []
    found = False
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
            
    if not found:
        lines.append(f"{key}={value}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def first_setup():
    print("=== CẤU HÌNH HỆ THỐNG LẦN ĐẦU ===")
    print("Nhấn Enter để bỏ qua nếu không muốn thay đổi giá trị hiện tại.\n")
    
    # 1. AI Config
    gemini_key = input("1. Nhập Gemini API Key (lấy tại aistudio.google.com): ").strip()
    if gemini_key:
        update_env_file("GEMINI_API_KEY", gemini_key)
        
    # 2. Telegram Config
    bot_token = input("2. Nhập Telegram Bot Token (lấy từ @BotFather): ").strip()
    if bot_token:
        update_env_file("TELEGRAM_BOT_TOKEN", bot_token)
        
    webhook_url = input("3. Nhập URL Webhook (ví dụ: https://abc.ngrok.io), để trống nếu dùng polling: ").strip()
    if webhook_url:
        update_env_file("WEBHOOK_URL", webhook_url)
        
    # 4. Email Config (Optional)
    setup_email = input("\nBạn có muốn cấu hình Email ngay không? (y/n): ").lower()
    if setup_email == 'y':
        update_env_file("SMTP_HOST", input("   - SMTP Host (VD: smtp.gmail.com): ").strip())
        update_env_file("SMTP_PORT", input("   - SMTP Port (VD: 587): ").strip())
        update_env_file("SMTP_USERNAME", input("   - Email đăng nhập: ").strip())
        update_env_file("SMTP_PASSWORD", input("   - Mật khẩu ứng dụng (App Password): ").strip())
        update_env_file("MAIL_FROM", input("   - Email gửi đi: ").strip())

    print("\n--- Cấu hình hoàn tất! ---")
    print("Các thông tin đã được lưu vào file API.env.")

if __name__ == "__main__":
    first_setup()
