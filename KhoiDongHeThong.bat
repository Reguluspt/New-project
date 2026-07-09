@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Khong mo duoc thu muc du an: %ROOT%
    pause
    exit /b 1
)

if "%FLASK_PORT%"=="" set "FLASK_PORT=5000"
set "PYTHONIOENCODING=utf-8"
set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Khong tim thay Python virtualenv tai:
    echo %PYTHON_EXE%
    echo.
    echo Hay chay CaiDat.bat truoc de tao moi truong Windows.
    pause
    exit /b 1
)

if not exist "%ROOT%logs" mkdir "%ROOT%logs" >nul 2>nul
if not exist "%ROOT%data" mkdir "%ROOT%data" >nul 2>nul

echo Dang kiem tra cac tien trinh ngam...
"%PYTHON_EXE%" -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('API.env')); load_dotenv(Path('.env')); from src.background_services import ensure_background_services; print(ensure_background_services())"
if errorlevel 1 (
    echo Khong khoi dong duoc tien trinh ngam. Kiem tra cau hinh API.env va log trong thu muc logs.
    pause
    exit /b 1
)

rem Kiem tra neu Flask da chay trong thu muc hien tai.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path '.').Path; $existing=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*api.run*' -and $_.CommandLine -like ('*' + $root + '*') } | Select-Object -First 1; if ($existing) { Set-Content -Path 'flask.pid' -Value $existing.ProcessId -Encoding ASCII; exit 0 } else { exit 1 }" >nul 2>nul
if not errorlevel 1 (
    set "OLD_PID="
    for /f "usebackq delims=" %%P in ("%ROOT%flask.pid") do set "OLD_PID=%%P"
    echo Flask da dang chay voi PID !OLD_PID!
    echo API: http://localhost:%FLASK_PORT%
    start "" "http://localhost:%FLASK_PORT%"
    pause
    exit /b 0
)

echo Dang khoi dong Flask API tai http://localhost:%FLASK_PORT% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path '.').Path; $python=$env:PYTHON_EXE; $stdout=Join-Path $root 'flask_stdout.log'; $stderr=Join-Path $root 'flask_stderr.log'; $pidPath=Join-Path $root 'flask.pid'; $args=@('-m','api.run','--port',$env:FLASK_PORT); $p=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru; Set-Content -Path $pidPath -Value $p.Id -Encoding ASCII; Write-Host $p.Id"
if errorlevel 1 (
    echo Khoi dong bai. Kiem tra log:
    echo %ROOT%flask_stderr.log
    pause
    exit /b 1
)

timeout /t 3 /nobreak >nul
start "" "http://localhost:%FLASK_PORT%"

echo Da khoi dong he thong.
echo PID Flask:
type "%ROOT%flask.pid"
echo.
echo Log Flask:
echo %ROOT%flask_stdout.log
echo %ROOT%flask_stderr.log
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
