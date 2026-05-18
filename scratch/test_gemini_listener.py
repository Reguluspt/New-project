import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path so we can import src
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.mail_listener import analyze_email_with_gemini, load_mail_listener_settings

def main():
    print("=== TEST GEMINI MAIL LISTENER ===")
    
    # Force load API.env
    env_path = PROJECT_ROOT / "API.env"
    print(f"Loading env from: {env_path}")
    load_dotenv(env_path, override=True)
    
    # Load settings through standard project function
    settings = load_mail_listener_settings()
    
    api_key = settings.gemini_api_key
    model = settings.gemini_model
    
    if not api_key:
        print("❌ LỖI: Không tìm thấy GEMINI_API_KEY trong API.env!")
        return
        
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "Too short"
    print(f"🔑 Gemini API Key: {masked_key}")
    print(f"🤖 Model: {model}")
    
    test_email = (
        "Chào anh/chị,\n\n"
        "Nhờ bên mình định giá tài sản giúp em:\n"
        "- Khách hàng: Nguyễn Văn A\n"
        "- Tài sản: Biệt thự tại 123 Đường Láng, phường Láng Thượng, quận Đống Đa, Hà Nội.\n"
        "- Số hồ sơ/hợp đồng: N26-00982.\n\n"
        "Cảm ơn anh/chị!"
    )
    
    print("\n--- Nội dung email mẫu ---")
    print(test_email)
    print("--------------------------")
    
    print("\n⏳ Đang gọi Gemini API để trích xuất thông tin...")
    try:
        extraction = analyze_email_with_gemini(test_email, api_key=api_key, model=model)
        print("\n✅ KẾT QUẢ THÀNH CÔNG!")
        print(f"👤 Khách hàng (customer_name): {extraction.customer_name}")
        print(f"📍 Địa chỉ (asset_address): {extraction.asset_address}")
        print(f"🆔 Mã hồ sơ (contract_id): {extraction.contract_id}")
        print(f"🎯 Độ tin cậy (confidence): {extraction.confidence}")
    except Exception as e:
        print(f"\n❌ LỖI KHI GỌI GEMINI API: {e}")

if __name__ == "__main__":
    main()
