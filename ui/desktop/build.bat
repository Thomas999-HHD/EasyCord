@echo off
REM ── EasyCord desktop build (Windows) ────────────────────────────────
REM   produces dist\EasyCord.exe  (single-file, no console)

setlocal
cd /d "%~dp0"

echo [1/3] Creating venv...
if not exist .venv ( py -3.11 -m venv .venv || goto :err )

call .venv\Scripts\activate.bat || goto :err

echo [2/3] Installing deps...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto :err

echo [3/3] Building EasyCord.exe...
pyinstaller --clean --noconfirm easycord.spec || goto :err

echo.
echo Done. Output: dist\EasyCord.exe
goto :eof

:err
echo Build failed.
exit /b 1
