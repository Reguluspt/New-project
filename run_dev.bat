@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [LOI] Khong tim thay .venv Windows. Hay chay CaiDat.bat truoc.
    pause
    exit /b 1
)

echo Starting Flask API on port 5000...
start "Flask API" cmd /k "cd /d ""%ROOT%"" && ""%PYTHON_EXE%"" -m api.run"

echo Starting React dev server on port 5173...
start "React Dev" cmd /k "cd /d ""%ROOT%web"" && npm run dev"

echo Both servers starting. API: http://localhost:5000, Web: http://localhost:5173
pause
exit /b 0
