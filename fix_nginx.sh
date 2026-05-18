#!/bin/bash

# Kịch bản tự động sửa lỗi 413 Payload Too Large của Nginx trên VPS
# Chạy kịch bản này dưới quyền root (sudo)

echo "Đang kiểm tra và sửa lỗi cấu hình Nginx (Tăng dung lượng tải file)..."

NGINX_CONF="/etc/nginx/nginx.conf"

if [ ! -f "$NGINX_CONF" ]; then
    echo "LỖI: Không tìm thấy tệp $NGINX_CONF. Có thể máy chủ không dùng Nginx mặc định."
    exit 1
fi

# Kiểm tra xem đã có cấu hình client_max_body_size chưa
if grep -q "client_max_body_size" "$NGINX_CONF"; then
    echo "Phát hiện cấu hình client_max_body_size cũ. Đang cập nhật lên 100M..."
    # Thay thế dòng cấu hình cũ bằng 100M
    sed -i 's/client_max_body_size.*/client_max_body_size 100M;/g' "$NGINX_CONF"
else
    echo "Chưa có cấu hình client_max_body_size. Đang thêm mới (100M) vào khối http..."
    # Chèn client_max_body_size 100M; ngay sau dòng http {
    sed -i '/http {/a \    client_max_body_size 100M;' "$NGINX_CONF"
fi

# Kiểm tra cú pháp cấu hình Nginx
echo "Kiểm tra cú pháp Nginx..."
nginx -t

if [ $? -eq 0 ]; then
    echo "Cú pháp Nginx hợp lệ. Đang khởi động lại Nginx..."
    systemctl restart nginx
    echo "✅ Sửa lỗi thành công! Anh hãy lên web tải lại trang (F5) và thử tải file lên lại nhé."
else
    echo "❌ LỖI: Cú pháp Nginx không hợp lệ. Vui lòng kiểm tra lại thủ công tệp $NGINX_CONF"
    exit 1
fi
