#!/bin/bash
# ==============================================================================
# HỆ THỐNG TỰ ĐỘNG KHỞI ĐỘNG TRÊN LINUX (STREAMLIT, BOT TELEGRAM, MAIL LISTENER)
# ==============================================================================

# Thiết lập bảng mã UTF-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8

# Xác định thư mục dự án
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || {
    echo "❌ Lỗi: Không thể di chuyển vào thư mục dự án: $ROOT"
    exit 1
}

# Cấu hình cổng và địa chỉ Streamlit mặc định
export STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
export STREAMLIT_ADDRESS="${STREAMLIT_ADDRESS:-0.0.0.0}"
PYTHON_EXE="$ROOT/.venv/bin/python"

# Kiểm tra virtualenv
if [ ! -f "$PYTHON_EXE" ]; then
    echo "❌ Không tìm thấy Python virtualenv tại: $PYTHON_EXE"
    echo "Vui lòng cài đặt môi trường trước bằng các lệnh sau:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Tạo thư mục log và dữ liệu nếu chưa có
mkdir -p "$ROOT/logs" "$ROOT/data"

echo "🔍 Đang kiểm tra và khởi động các dịch vụ chạy ngầm..."
"$PYTHON_EXE" -c "
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('API.env'))
load_dotenv(Path('.env'))
from src.background_services import ensure_background_services
print('Dịch vụ ngầm:', ensure_background_services())
"
if [ $? -ne 0 ]; then
    echo "❌ Lỗi: Không khởi động được dịch vụ ngầm. Hãy kiểm tra file log trong thư mục 'logs/'"
    exit 1
fi

# Kiểm tra nếu Streamlit đã chạy sẵn
STREAMLIT_PID_FILE="$ROOT/streamlit.pid"
if [ -f "$STREAMLIT_PID_FILE" ]; then
    OLD_PID=$(cat "$STREAMLIT_PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✨ Hệ thống đã chạy sẵn với PID Streamlit: $OLD_PID"
        echo "🔗 Địa chỉ truy cập Streamlit: http://localhost:$STREAMLIT_PORT"
        exit 0
    fi
fi

echo "🚀 Đang khởi động Streamlit..."
STDOUT_LOG="$ROOT/logs/streamlit_stdout.log"
STDERR_LOG="$ROOT/logs/streamlit_stderr.log"

# Khởi chạy Streamlit bằng nohup
nohup "$PYTHON_EXE" -m streamlit run app.py \
    --server.port "$STREAMLIT_PORT" \
    --server.address "$STREAMLIT_ADDRESS" \
    > "$STDOUT_LOG" 2> "$STDERR_LOG" &

ST_PID=$!
echo "$ST_PID" > "$STREAMLIT_PID_FILE"

sleep 2

# Kiểm tra xem Streamlit có khởi chạy thành công không
if kill -0 "$ST_PID" 2>/dev/null; then
    echo "✅ Đã khởi động hệ thống thành công!"
    echo "PID Streamlit: $ST_PID"
    echo "🔗 Địa chỉ truy cập Streamlit: http://localhost:$STREAMLIT_PORT"
    echo "📝 Đường dẫn ghi nhận log: logs/streamlit_stderr.log"
else
    echo "❌ Khởi động Streamlit thất bại. Chi tiết lỗi:"
    cat "$STDERR_LOG"
    exit 1
fi

exit 0
