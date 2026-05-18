# Mail Feature Code Package

Gói này chứa toàn bộ mã nguồn liên quan đến tính năng Mail/Gmail/Telegram listener để gửi đối tác kỹ thuật xem xét.

## Thành phần chính

- `src/mail_service.py`: gửi email qua Gmail SMTP bằng `aiosmtplib`, hỗ trợ `MAIL_TO`, `MAIL_CC`, subject tự động và render HTML.
- `src/mail_renderer.py`: model dữ liệu email, render `mail_template.html` bằng Jinja2, tạo preview gửi qua Telegram.
- `src/mail_listener.py`: lắng nghe Gmail IMAP, dùng Gemini để đối soát email, reply tự động, cập nhật SQLite, log xử lý, chống phản hồi trùng.
- `src/templates/mail_template.html`: template HTML bảng thông tin hồ sơ gửi qua email.
- `src/contracts.py`: rút gọn số hợp đồng như `010/2026/N04.1027/DN -> N04.1027`.
- `src/telegram_server.py`: phần tích hợp Telegram, gồm các lệnh `/gui_mail`, `/listener_on`, `/listener_off`, `/listener_status`, `/listener_log`.

## Test liên quan

- `tests/test_mail_service.py`
- `tests/test_mail_renderer.py`
- `tests/test_mail_listener.py`
- `tests/test_contracts.py`

## Biến môi trường cần cấu hình

Xem file `API.env.example`. Không dùng trực tiếp file `API.env` thật vì có token và mật khẩu ứng dụng Gmail.

## Luồng xử lý chính

1. Telegram bot hoặc phần mềm gọi `send_appraisal_email()` để gửi email yêu cầu định giá.
2. `mail_listener.py` chạy nền và quét Gmail qua IMAP.
3. Với email chưa đọc, listener gửi nội dung sang Gemini để trích xuất `contract_id`, tên khách hàng, địa chỉ tài sản và độ tin cậy.
4. Listener đối soát với SQLite `records`.
5. Nếu match trên ngưỡng, listener reply email bằng `mail_template.html`, cập nhật trạng thái hồ sơ thành `Sẵn sàng nhập web`.
6. Email đã xử lý được ghi vào bảng `processed_emails` để tránh phản hồi trùng.
7. Sự kiện được ghi vào `logs/mail_listener_events.jsonl` với các trạng thái `matched`, `skipped`, `replied`, `failed`.

## Lệnh Telegram

- `/gui_mail N04-1051`: gửi mail yêu cầu định giá theo số hợp đồng rút gọn.
- `/listener_on`: bật listener và đảm bảo tiến trình nền đang chạy.
- `/listener_off`: tắt theo dõi Gmail.
- `/listener_status`: xem trạng thái listener.
- `/listener_log`: gửi 10 dòng log listener gần nhất.

## Ghi chú bảo mật

Đối tác cần tự cấu hình Gmail App Password, Telegram Bot Token và Gemini API Key trong môi trường triển khai. Không hard-code các thông tin này vào source code.
