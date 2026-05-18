# Hướng Dẫn Vận Hành & Khởi Động Lại Hệ Thống Trên VPS Linux

Tài liệu này lưu trữ thông tin cấu hình, danh sách dịch vụ và các cú pháp vận hành quan trọng của phần mềm Định giá (Appraisal System) chạy trên VPS Linux của anh/chị.

---

## 1. Thông Tin Môi Trường & Dịch Vụ
* **Đường dẫn dự án trên VPS:** `/root/app` (hoặc `~/app`)
* **Hệ quản lý tiến trình:** Systemd (`systemctl`)
* **Danh sách các dịch vụ (Services):**
  1. `streamlit.service` — Streamlit Appraisal App (Ứng dụng giao diện web định giá)
  2. `telegram-bot.service` — Appraisal Telegram Bot Webhook Server (Bot Telegram thẩm định)
  3. `mail-listener.service` — Appraisal Mail Listener Service (Dịch vụ đọc & phản hồi email tự động)

---

## 2. Bảng Tra Cứu Lệnh Vận Hành Nhanh

| Mục tiêu | Lệnh thực thi trên VPS |
| :--- | :--- |
| **Khởi động lại Mail Listener** | `systemctl restart mail-listener.service` |
| **Khởi động lại Telegram Bot** | `systemctl restart telegram-bot.service` |
| **Khởi động lại Streamlit App** | `systemctl restart streamlit.service` |
| **Khởi động lại toàn bộ hệ thống** | `systemctl restart telegram-bot.service streamlit.service mail-listener.service` |
| **Kiểm tra trạng thái các dịch vụ** | `systemctl status telegram-bot.service streamlit.service mail-listener.service` |

---

## 3. Xem Log Trực Tiếp (Real-time Logs)

Để theo dõi hoạt động hoặc chẩn đoán lỗi của từng dịch vụ, sử dụng công cụ `journalctl` (nhấn `Ctrl + C` để thoát màn hình log):

* **Theo dõi Telegram Bot:**
  ```bash
  journalctl -u telegram-bot.service -f -n 100
  ```
* **Theo dõi Streamlit App:**
  ```bash
  journalctl -u streamlit.service -f -n 100
  ```
* **Theo dõi Mail Listener:**
  ```bash
  journalctl -u mail-listener.service -f -n 100
  # Hoặc xem file log sự kiện dạng JSONL:
  tail -f /root/app/logs/mail_listener_events.jsonl
  ```

---

## 4. Quy Trình Cập Nhật Code từ GitHub
Khi có tính năng hoặc sửa lỗi mới trên nhánh `feature/delete-case-button`, quy trình deploy chuẩn như sau:

```bash
# 1. Truy cập thư mục app
cd /root/app

# 2. Kéo code mới từ GitHub
git pull origin feature/delete-case-button

# 3. Khởi động lại các dịch vụ có liên quan (ví dụ cả 3 dịch vụ)
systemctl restart telegram-bot.service streamlit.service mail-listener.service
```

---

## 5. Hướng Dẫn Xử Lý Lỗi API Key Hết Hạn
Nếu trong log xuất hiện lỗi `"API key expired. Please renew the API key."` hoặc `"API_KEY_INVALID"`, hãy thực hiện:

1. Mở tệp cấu hình trên VPS để chỉnh sửa:
   ```bash
   nano /root/app/API.env
   # Hoặc: nano /root/app/.env
   ```
2. Cập nhật khóa API mới vào tham số cấu hình tương ứng (ví dụ: `GEMINI_API_KEY`).
3. Lưu lại bằng tổ hợp phím: `Ctrl + O` -> Nhấn `Enter` -> `Ctrl + X` để thoát.
4. Áp dụng cấu hình mới bằng cách khởi động lại dịch vụ:
   ```bash
   systemctl restart mail-listener.service telegram-bot.service
   ```
