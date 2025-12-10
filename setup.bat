@echo off
REM Setup script for Apple Subscription Validator (Windows)

echo ==========================================
echo Apple Subscription Validator - Setup
echo ==========================================
echo.

REM Check Python version
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found!
    echo Please install Python 3.7 or higher from python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Found: %PYTHON_VERSION%
echo.

REM Install dependencies
echo Installing dependencies...
echo.

python -m pip install PyJWT[crypto]==2.8.0 cryptography==41.0.7 requests==2.31.0

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo Setup Complete!
    echo ==========================================
    echo.
    echo You can now run:
    echo   python validate_from_file.py receipt.txt "your_secret"
    echo   python interactive_validator.py
    echo.
) else (
    echo.
    echo Installation failed!
    echo Try running manually:
    echo   pip install PyJWT[crypto] cryptography requests
    pause
    exit /b 1
)

pause
