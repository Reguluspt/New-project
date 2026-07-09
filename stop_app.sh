#!/bin/bash
# ==============================================================================
# ĐÓNG ỨNG DỤNG VÀ CÁC TIẾN TRÌNH CHẠY NGẦM TRÊN LINUX
# ==============================================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

echo "==================================================="
echo "  ĐANG ĐÓNG ỨNG DỤNG VÀ CÁC TIẾN TRÌNH CHẠY NGẦM"
echo "==================================================="
echo ""

# Danh sách các tệp tin chứa PID cần dừng
PID_FILES=(
    "$ROOT/streamlit.pid"
    "$ROOT/telegram.pid"
    "$ROOT/data/mail_listener.pid"
    "$ROOT/data/ngrok.pid"
    "$ROOT/flask.pid"
)

# Hàm tắt tiến trình bằng PID
terminate_pid() {
    local pid_file="$1"
    local name="$2"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ]; then
            if kill -0 "$pid" 2>/dev/null; then
                echo "⏳ Đang đóng $name (PID: $pid)..."
                kill "$pid" 2>/dev/null
                
                # Chờ tối đa 5 giây để tiến trình tắt hẳn
                for i in {1..5}; do
                    if ! kill -0 "$pid" 2>/dev/null; then
                        break
                    fi
                    sleep 1
                done

                # Nếu vẫn chưa tắt, force kill
                if kill -0 "$pid" 2>/dev/null; then
                    echo "⚠️ Cảnh báo: $name chưa tắt, đang cưỡng chế dừng (SIGKILL)..."
                    kill -9 "$pid" 2>/dev/null
                fi
            fi
        fi
        rm -f "$pid_file"
    fi
}

# Tắt các tiến trình thông qua PID file
terminate_pid "$ROOT/streamlit.pid" "Streamlit App"
terminate_pid "$ROOT/telegram.pid" "Telegram Bot Webhook"
terminate_pid "$ROOT/data/mail_listener.pid" "Mail Listener Service"
terminate_pid "$ROOT/data/ngrok.pid" "Ngrok Service"
terminate_pid "$ROOT/flask.pid" "Flask API Service"

# Tìm và dọn dẹp các tiến trình python chạy ngầm còn dư trong thư mục này
echo "🔍 Đang tìm các tiến trình Python còn sót lại trong thư mục dự án..."
CURRENT_USER=$(whoami)
# Lấy danh sách tiến trình Python đang chạy liên quan đến dự án của user hiện tại
RESIDUAL_PIDS=$(ps -u "$CURRENT_USER" -o pid,cmd | grep -E "python.*(app\.py|telegram_server|mail_listener|api\.run)" | grep -v grep | awk '{print $1}')

if [ -n "$RESIDUAL_PIDS" ]; then
    for pid in $RESIDUAL_PIDS; do
        echo "🧹 Đang dọn dẹp tiến trình python dư thừa (PID: $pid)..."
        kill -9 "$pid" 2>/dev/null
    done
fi

echo ""
echo "==================================================="
echo "  ĐÃ ĐÓNG THÀNH CÔNG TẤT CẢ TIẾN TRÌNH CỦA BOT/APP!"
echo "==================================================="
exit 0
