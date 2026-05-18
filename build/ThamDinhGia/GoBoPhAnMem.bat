@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

echo ===================================================
echo   GO BO PHAN MEM THAM DINH GIA
echo ===================================================
echo.
echo CANH BAO: Thao tac nay se xoa toan bo phan mem,
echo bao gom ca du lieu va cau hinh tren may tinh nay.
echo.

set /p CONFIRM="Ban co chac chan muon go bo? Nhap 'GO BO' de tiep tuc: "
if /i not "%CONFIRM%"=="GO BO" (
    echo Da huy thao tac go bo.
    pause
    exit /b 0
)

set "ROOT=%~dp0"
cd /d "%ROOT%"

:: 1. Tat tat ca cac tien trinh dang chay
echo.
echo [1/4] Dang tat cac tien trinh cua phan mem...
for /f "tokens=2 delims==" %%A in ('wmic process where "name='python.exe' and commandline like '%%ThamDinhGia%%'" get processid /value 2^>nul') do (
    if "%%A" NEQ "" (
        echo   Dang dong PID: %%A
        taskkill /PID %%A /F >nul 2>&1
    )
)
:: Tat ngrok neu dang chay
for /f "tokens=2 delims==" %%A in ('wmic process where "name='ngrok.exe'" get processid /value 2^>nul') do (
    if "%%A" NEQ "" (
        echo   Dang dong Ngrok PID: %%A
        taskkill /PID %%A /F >nul 2>&1
    )
)
echo   Da tat xong cac tien trinh.

:: 2. Xoa Shortcut tren Desktop
echo [2/4] Dang xoa Shortcut tren Desktop...
del "%USERPROFILE%\Desktop\Tham Dinh Gia - Bat.lnk" 2>nul
del "%USERPROFILE%\Desktop\Tham Dinh Gia - Tat.lnk" 2>nul
echo   Da xoa Shortcut.

:: 3. Hoi nguoi dung co muon sao luu du lieu truoc khi xoa khong
set /p BACKUP="Ban co muon sao luu du lieu truoc khi xoa? (y/n): "
if /i "%BACKUP%"=="y" (
    echo   Dang tao ban sao luu cuoi cung...
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" -c "from src.data_manager import create_backup, get_backup_bytes; p = create_backup(); import shutil; shutil.copy2(p, '%USERPROFILE%\\Desktop\\ThamDinhGia_backup_final.zip')" 2>nul
        if not errorlevel 1 (
            echo   Da luu ban sao len Desktop: ThamDinhGia_backup_final.zip
        ) else (
            echo   Khong the tao sao luu tu dong. Ban co the copy thu cong thu muc 'data' truoc khi tiep tuc.
            pause
        )
    ) else (
        echo   Khong tim thay Python. Ban co the copy thu cong thu muc 'data' truoc khi tiep tuc.
        pause
    )
)

:: 4. Xoa thu muc phan mem
echo [3/4] Dang xoa thu muc phan mem...
echo   Thu muc se bi xoa: %ROOT%
echo.

:: Tao script tam de tu xoa chinh no sau khi bat ket thuc
set "SELF_DELETE_SCRIPT=%TEMP%\delete_thamdingia.bat"
(
    echo @echo off
    echo timeout /t 3 /nobreak ^>nul
    echo rd /s /q "%ROOT%"
    echo if exist "%ROOT%" (
    echo     echo Khong the xoa hoan toan. Vui long xoa thu cong thu muc:
    echo     echo %ROOT%
    echo     pause
    echo ^) else (
    echo     echo.
    echo     echo ===================================================
    echo     echo   DA GO BO PHAN MEM THANH CONG!
    echo     echo ===================================================
    echo     echo.
    echo     pause
    echo ^)
    echo del "%%~f0"
) > "%SELF_DELETE_SCRIPT%"

echo [4/4] Dang hoan tat go bo...
echo.
echo ===================================================
echo   Phan mem se duoc xoa trong giay lat.
echo ===================================================
echo.

:: Chay script tu xoa va thoat
start "" "%SELF_DELETE_SCRIPT%"
exit /b 0
