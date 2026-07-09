@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Khong mo duoc thu muc du an.
    pause
    exit /b 1
)

echo ===================================================
echo DANG DONG UNG DUNG VA CAC TIEN TRINH CHAY NGAM
echo ===================================================
echo.

if exist "%ROOT%flask.pid" (
    for /f "usebackq delims=" %%P in ("%ROOT%flask.pid") do (
        if not "%%P"=="" (
            echo Dang dong Flask PID: %%P
            taskkill /PID %%P /F >nul 2>&1
        )
    )
    del "%ROOT%flask.pid" >nul 2>nul
)

if exist "%ROOT%telegram.pid" (
    for /f "usebackq delims=" %%P in ("%ROOT%telegram.pid") do (
        if not "%%P"=="" (
            echo Dang dong Telegram PID: %%P
            taskkill /PID %%P /F >nul 2>&1
        )
    )
    del "%ROOT%telegram.pid" >nul 2>nul
)

if exist "%ROOT%data\mail_listener.pid" (
    for /f "usebackq delims=" %%P in ("%ROOT%data\mail_listener.pid") do (
        if not "%%P"=="" (
            echo Dang dong Mail listener PID: %%P
            taskkill /PID %%P /F >nul 2>&1
        )
    )
    del "%ROOT%data\mail_listener.pid" >nul 2>nul
)

if exist "%ROOT%data\ngrok.pid" (
    for /f "usebackq delims=" %%P in ("%ROOT%data\ngrok.pid") do (
        if not "%%P"=="" (
            echo Dang dong Ngrok PID: %%P
            taskkill /PID %%P /F >nul 2>&1
        )
    )
    del "%ROOT%data\ngrok.pid" >nul 2>nul
)

rem Dong cac tien trinh Python dang chay tu dung thu muc du an nay.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path '.').Path; Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like ('*' + $root + '*') } | ForEach-Object { Write-Host ('Dang dong PID: ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo.
echo ===================================================
echo DA DONG CAC TIEN TRINH CUA APP TRONG THU MUC NAY
echo ===================================================
pause
exit /b 0
