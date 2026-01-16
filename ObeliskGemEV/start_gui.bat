@echo off
REM Startet das ObeliskGemEV GUI

cd /d "%~dp0"

REM Versuche verschiedene Python-Befehle
python gui.py 2>nul
if %errorlevel% equ 0 goto :end

py gui.py 2>nul
if %errorlevel% equ 0 goto :end

python3 gui.py 2>nul
if %errorlevel% equ 0 goto :end

echo.
echo ========================================
echo Fehler beim Starten des GUI!
echo ========================================
echo.
echo Python wurde nicht gefunden.
echo Bitte stellen Sie sicher, dass Python installiert ist.
echo.
echo Versuchen Sie manuell:
echo   python gui.py
echo   oder
echo   py gui.py
echo.
pause
exit /b 1

:end
exit /b 0
