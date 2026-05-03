@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Khong mo duoc thu muc du an: %ROOT%
    pause
    exit /b 1
)

if "%STREAMLIT_PORT%"=="" set "STREAMLIT_PORT=8501"
if "%STREAMLIT_ADDRESS%"=="" set "STREAMLIT_ADDRESS=0.0.0.0"
set "PYTHONIOENCODING=utf-8"
set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Khong tim thay Python virtualenv tai:
    echo %PYTHON_EXE%
    echo.
    echo Hay cai dat truoc:
    echo python -m venv .venv
    echo .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%ROOT%logs" mkdir "%ROOT%logs" >nul 2>nul
if not exist "%ROOT%data" mkdir "%ROOT%data" >nul 2>nul

echo Dang kiem tra cac tien trinh ngam...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%PYTHON_EXE%' -c \"from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('API.env')); load_dotenv(Path('.env')); from src.background_services import ensure_background_services; print(ensure_background_services())\""
if errorlevel 1 (
    echo Khong khoi dong duoc tien trinh ngam. Kiem tra cau hinh API.env va log trong thu muc logs.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path '.').Path; $existing=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*-m streamlit run app.py*' -and $_.CommandLine -like ('*' + $root + '*') } | Select-Object -First 1; if ($existing) { Set-Content -Path (Join-Path $root 'streamlit.pid') -Value $existing.ProcessId -Encoding ASCII; exit 0 }; exit 1" >nul 2>nul
if not errorlevel 1 (
    set "OLD_PID="
    for /f "usebackq delims=" %%P in ("%ROOT%streamlit.pid") do set "OLD_PID=%%P"
    echo He thong dang chay san voi PID Streamlit: !OLD_PID!
    echo Mo trinh duyet: http://localhost:%STREAMLIT_PORT%
    start "" "http://localhost:%STREAMLIT_PORT%"
    pause
    exit /b 0
)

echo Dang khoi dong he thong...
echo - Ung dung Streamlit: http://localhost:%STREAMLIT_PORT%
echo - Telegram webhook, mail listener va ngrok se chay ngam neu duoc bat trong cau hinh.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path '.').Path; $python=$env:PYTHON_EXE; $stdout=Join-Path $root 'streamlit_stdout.log'; $stderr=Join-Path $root 'streamlit_stderr.log'; $pidPath=Join-Path $root 'streamlit.pid'; $args=@('-m','streamlit','run','app.py','--server.port',$env:STREAMLIT_PORT,'--server.address',$env:STREAMLIT_ADDRESS); $p=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru; Set-Content -Path $pidPath -Value $p.Id -Encoding ASCII; Write-Host $p.Id"
if errorlevel 1 (
    echo Khoi dong that bai. Kiem tra log:
    echo %ROOT%streamlit_stderr.log
    pause
    exit /b 1
)

timeout /t 3 /nobreak >nul
start "" "http://localhost:%STREAMLIT_PORT%"

echo Da khoi dong he thong.
echo PID Streamlit: 
type "%ROOT%streamlit.pid"
echo.
echo Log Streamlit:
echo %ROOT%streamlit_stdout.log
echo %ROOT%streamlit_stderr.log
echo.
echo PID cac tien trinh ngam neu duoc bat:
if exist "%ROOT%telegram.pid" (
    echo - Telegram:
    type "%ROOT%telegram.pid"
)
if exist "%ROOT%data\mail_listener.pid" (
    echo - Mail listener:
    type "%ROOT%data\mail_listener.pid"
)
if exist "%ROOT%data\ngrok.pid" (
    echo - Ngrok:
    type "%ROOT%data\ngrok.pid"
)
echo.
pause
exit /b 0
