@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [LOI] Khong tim thay moi truong ao. Vui long chay CaiDat.bat truoc.
    pause
    exit /b 1
)

"%PYTHON_EXE%" tools/first_setup.py

echo.
echo Da luu cau hinh. Bay gio ban co the chay 'KhoiDongHeThong.bat'.
pause
exit /b 0
