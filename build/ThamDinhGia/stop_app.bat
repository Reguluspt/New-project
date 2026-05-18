@echo off
chcp 65001 >nul
echo ===================================================
echo   DANG DONG UNG DUNG VA CAC TIEN TRINH CHAY NGAM
echo ===================================================
echo.

:: Tim va dong toan bo cac tien trinh Python trong thu muc du an bang WMIC
for /f "tokens=2 delims==" %%A in ('wmic process where "name='python.exe' and commandline like '%%New project%%'" get processid /value 2^>nul') do (
    if "%%A" NEQ "" (
        echo Dang dong PID: %%A
        taskkill /PID %%A /F >nul 2>&1
    )
)

echo.
echo ===================================================
echo   DA DONG THANH CONG TAT CA TIEN TRINH CUA BOT/APP!
echo ===================================================
pause
