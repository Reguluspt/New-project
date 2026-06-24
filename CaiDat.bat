@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

echo ===================================================
echo   CHƯƠNG TRÌNH CÀI ĐẶT HỆ THỐNG THẨM ĐỊNH GIÁ
echo ===================================================
echo.

set "ROOT=%~dp0"
cd /d "%ROOT%"

:: 1. Kiểm tra Python
echo [1/7] Đang kiểm tra môi trường Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo LỖI: Không tìm thấy Python trên máy tính của bạn.
    echo Vui lòng tải và cài đặt Python 3.11 hoặc mới hơn tại: https://www.python.org/downloads/
    echo LƯU Ý: Hãy tích chọn "Add Python to PATH" khi cài đặt.
    echo.
    pause
    exit /b 1
)

:: 2. Tạo Virtual Environment
echo [2/7] Đang khởi tạo môi trường ảo (.venv)...
if exist ".venv" (
    echo Môi trường ảo đã tồn tại, bỏ qua bước này.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo LỖI: Không thể tạo môi trường ảo.
        pause
        exit /b 1
    )
)

:: 3. Cài đặt thư viện Python
echo [3/7] Đang cài đặt các thư viện Python (Yêu cầu Internet)...
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo LỖI: Cài đặt thư viện thất bại. Vui lòng kiểm tra kết nối Internet.
    pause
    exit /b 1
)

:: 3.5. Cài đặt Node.js dependencies cho React frontend
echo.
echo [4/7] Đang kiểm tra Node.js cho giao diện React...
where node >nul 2>nul
if errorlevel 1 (
    echo CẢNH BÁO: Không tìm thấy Node.js. Bỏ qua build React frontend.
    echo Hãy cài đặt Node.js >= 18 tại: https://nodejs.org và chạy lại CaiDat.bat.
) else (
    if exist "web\node_modules" (
        echo Node dependencies đã có, bỏ qua.
    ) else (
        echo Đang cài đặt npm packages...
        cd /d "%ROOT%web"
        npm install
        if errorlevel 1 (
            echo CẢNH BÁO: npm install thất bại. Giao diện web chưa sẵn sàng.
        ) else (
            echo Node packages đã cài xong.
        )
        cd /d "%ROOT%"
    )
)

:: 4. Cài đặt Playwright
echo [5/7] Đang cài đặt trình duyệt tự động (Playwright)...
playwright install chromium
if errorlevel 1 (
    echo CẢNH BÁO: Không thể cài đặt trình duyệt tự động. Tính năng nhập web có thể không hoạt động.
)

:: 4.5. Tải Ngrok (Tùy chọn cho Telegram Webhook)
echo [5.5/7] Đang tải Ngrok (Dùng cho Telegram Webhook)...
if exist "ngrok.exe" (
    echo Ngrok đã tồn tại, bỏ qua bước này.
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "try { " ^
        "  $url = 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip'; " ^
        "  $dest = Join-Path $pwd 'ngrok.zip'; " ^
        "  Invoke-WebRequest -Uri $url -OutFile $dest; " ^
        "  Expand-Archive -Path $dest -DestinationPath $pwd -Force; " ^
        "  Remove-Item $dest; " ^
        "  Write-Host 'Đã tải và giải nén Ngrok thành công.' " ^
        "} catch { " ^
        "  Write-Warning 'Không thể tải Ngrok tự động. Bạn có thể tự tải tại ngrok.com' " ^
        "}"
)

:: 5. Khởi tạo tệp tin và Database
echo [6/7] Đang thiết lập tệp tin cấu hình và Database...
if not exist "API.env" (
    if exist "API.env.example" (
        copy "API.env.example" "API.env" >nul
    ) else (
        echo. > "API.env"
    )
)

:: Cập nhật đường dẫn Ngrok vào API.env nếu chưa có
findstr /C:"NGROK_PATH=" "API.env" >nul
if errorlevel 1 (
    echo. >> "API.env"
    echo NGROK_PATH=ngrok.exe >> "API.env"
)

:: Khởi tạo database trống
python -c "from src.sqlite_store import init_db; from pathlib import Path; init_db(Path('data/cases.db'))"
python -c "from src.database_manager import ensure_tracking_record_schema; from pathlib import Path; import asyncio; asyncio.run(ensure_tracking_record_schema(Path('data/telegram_records.db')))"

:: 6. Tạo Shortcut Desktop
echo [7/7] Đang tạo Shortcut trên Desktop...
set "SCRIPT_KH_PATH=%ROOT%KhoiDongHeThong.bat"
set "SCRIPT_TAT_PATH=%ROOT%stop_app.bat"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut(\"$env:USERPROFILE\Desktop\Tham Dinh Gia - Bat.lnk\"); " ^
    "$s.TargetPath = '%SCRIPT_KH_PATH%'; " ^
    "$s.WorkingDirectory = '%ROOT%'; " ^
    "$s.Save(); " ^
    "$s2 = $ws.CreateShortcut(\"$env:USERPROFILE\Desktop\Tham Dinh Gia - Tat.lnk\"); " ^
    "$s2.TargetPath = '%SCRIPT_TAT_PATH%'; " ^
    "$s2.WorkingDirectory = '%ROOT%'; " ^
    "$s2.Save();"

echo.
echo ===================================================
echo   CÀI ĐẶT HOÀN TẤT!
echo ===================================================
echo.
echo HƯỚNG DẪN TIẾP THEO:
echo 1. Hãy chạy file 'CauHinhBanDau.bat' để nhập API Key và Token.
echo 2. Chạy 'build_production.bat' để build giao diện React (lần đầu).
echo 3. Sử dụng Shortcut trên Desktop để Bật/Tắt ứng dụng.
echo.
pause
exit /b 0
