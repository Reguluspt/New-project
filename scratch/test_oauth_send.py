import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

import asyncio
from src.oauth2_service import send_email_via_oauth2

async def main():
    print("Starting test email send via Gmail API (OAuth2)...")
    try:
        msg_id = await send_email_via_oauth2(
            provider="google",
            from_email="hostktpro@gmail.com",
            to_email="hostktpro@gmail.com",
            subject="HE THONG THAM DINH - KET NOI OAUTH2 THANH CONG!",
            html_body="""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 12px; background-color: #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <div style="text-align: center; padding-bottom: 20px; border-bottom: 2px solid #f0f0f0;">
                    <h2 style="color: #4caf50; margin: 0;">🎉 Kết Nối Thành Công!</h2>
                </div>
                <div style="padding: 20px 0; line-height: 1.6; color: #333333;">
                    <p>Chào anh,</p>
                    <p>Đây là email kiểm thử tự động được gửi trực tiếp qua <strong>Google Workspace REST API (OAuth2)</strong> của anh.</p>
                    <p>Việc nhận được email này chứng minh dự án đã liên kết an toàn và thành công 100% với tài khoản Google. Từ nay các hoạt động gửi/nhận email thẩm định giá sẽ chạy mượt mà trên hạ tầng API REST cao cấp và cực kỳ bảo mật.</p>
                    <div style="background-color: #f9f9f9; padding: 15px; border-radius: 8px; border-left: 4px solid #4caf50; margin: 20px 0;">
                        <strong>Thông số kết nối:</strong><br>
                        • Provider: Google Workspace (Gmail API)<br>
                        • Email: hostktpro@gmail.com<br>
                        • Phương thức: OAuth2 REST API (Không dùng IMAP/SMTP truyền thống)
                    </div>
                </div>
                <div style="text-align: center; padding-top: 20px; border-top: 1px solid #f0f0f0; font-size: 12px; color: #888888;">
                    Hệ thống Thẩm định giá Nội bộ • CenValue
                </div>
            </div>
            """
        )
        print(f"SUCCESS: Email sent successfully! Message ID: {msg_id}")
    except Exception as e:
        print(f"ERROR: Email sending failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
