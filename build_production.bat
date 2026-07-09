@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Khong mo duoc thu muc du an.
    pause
    exit /b 1
)

echo ============================================
echo Production Build - He thong Tham dinh
echo ============================================
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay Node.js. Hay cai dat Node.js >= 18.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay npm. Hay cai dat npm.
    pause
    exit /b 1
)

echo [1/3] Kiem tra node_modules...
if not exist "%ROOT%web\node_modules" (
    echo Chua co node_modules, dang cai dat...
    cd /d "%ROOT%web"
    npm install
    if errorlevel 1 (
        echo [LOI] npm install bai.
        pause
        exit /b 1
    )
    cd /d "%ROOT%"
)

echo [2/3] Dang build React SPA...
cd /d "%ROOT%web"
npm run build
if errorlevel 1 (
    echo [LOI] Build bai. Kiem tra loi o tren.
    cd /d "%ROOT%"
    pause
    exit /b 1
)
cd /d "%ROOT%"

echo [3/3] Build hoan tat!
echo OK - File dau ra tai: web\dist\
pause
exit /b 0
