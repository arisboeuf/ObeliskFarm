@echo off
REM Starts the ObeliskFarm GUI (from source)

cd /d "%~dp0"

REM Try common Python launch commands
python gui.py 2>nul
if %errorlevel% equ 0 goto :end

py gui.py 2>nul
if %errorlevel% equ 0 goto :end

python3 gui.py 2>nul
if %errorlevel% equ 0 goto :end

echo.
echo ========================================
echo Failed to start the GUI!
echo ========================================
echo.
echo Python was not found.
echo Please make sure Python is installed.
echo.
echo Try manually:
echo   python gui.py
echo   or
echo   py gui.py
echo.
pause
exit /b 1

:end
exit /b 0
