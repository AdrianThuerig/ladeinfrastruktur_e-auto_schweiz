@echo off
:: Change directory to script location
cd /d "%~dp0"

:: Check if python is available in PATH
python --version >nul 2>&1
if %errorlevel% equ 0 (
    python start.py
) else (
    :: Fallback to the Python Launcher (py.exe)
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        py -3 start.py
    ) else (
        echo Error: Python was not found in PATH. Please install Python 3.
        pause
    )
)
