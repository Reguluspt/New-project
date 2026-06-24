# Cập nhật ứng dụng trên VPS

Mã nguồn không còn phụ thuộc vào đường dẫn `E:\New project`:

- Mẫu biểu trong `data/template_config.json` dùng đường dẫn tương đối với thư mục dự án.
- `RECORDS_DB_PATH` dùng đường dẫn tương đối sẽ được tính từ thư mục dự án. Nếu cấu hình cũ chứa đường dẫn Windows, Linux tự dùng `data/telegram_records.db` thay vì tạo một tệp sai tên.

Trên VPS, thực hiện tại thư mục ứng dụng (ví dụ `/root/app`):

```bash
cd /root/app
git pull

# Giữ lại dữ liệu và cấu hình bí mật hiện có; không chép đè API.env hay data/oauth_config.json.
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests/test_mail_listener.py tests/test_template_history.py

sudo systemctl restart telegram-bot.service
sudo systemctl restart mail-listener.service
sudo systemctl restart streamlit.service
sudo systemctl status telegram-bot.service mail-listener.service streamlit.service --no-pager
```

Đặt trong `API.env` (nếu dịch vụ đang dùng biến này):

```dotenv
RECORDS_DB_PATH=data/telegram_records.db
```

Nếu cơ sở dữ liệu trên VPS đang nằm ở vị trí khác, giữ nguyên đường dẫn Linux tuyệt đối hiện tại thay vì dùng giá trị trên.
