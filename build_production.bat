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
echo   Production Build - He thong Tham dinh
echo ============================================
echo.

rem --- Kiem tra Node.js ---
where node >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay Node.js. Hay cai dat Node.js >= 18.
    pause
    exit /b 1
)

rem --- Kiem tra npm ---
where npm >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay npm. Hay cai dat npm.
    pause
    exit /b 1
)

rem --- Cai dat dependencies neu chua co ---
echo [1/3] Kiem tra node_modules...
if not exist "%ROOT%web\node_modules" (
    echo     Chua co node_modules, dang cai dat...
    cd /d "%ROOT%web"
    npm install
    if errorlevel 1 (
        echo [LOI] npm install that bai.
        pause
        exit /b 1
    )
    cd /d "%ROOT%"
)

rem --- Build React SPA ---
echo [2/3] Dang build React SPA...
cd /d "%ROOT%web"
npm run build
if errorlevel 1 (
    echo [LOI] Build that bai. Kiem tra loi o tren.
    cd /d "%ROOT%"
    pause
    exit /b 1
)
cd /d "%ROOT%"
echo     OK - File dau ra tai: web\dist\

rem --- Thong bao hoan thanh ---
echo [3/3] Build hoan tat!
echo.
echo ============================================
echo  De chay production:
echo    .venv\Scripts\python.exe -m api.run
echo.
echo  Hoac set FLASK_DEBUG=false truoc khi chay
echo  de Flask tu phuc vu cac file React static.
echo ============================================
echo.
pause
exit /b 0
