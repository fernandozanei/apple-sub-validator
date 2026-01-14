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

python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo Installation failed!
    echo Try running manually:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Create .env file from template if it doesn't exist
echo.
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo Created .env file
    echo.
    echo IMPORTANT: Edit .env file and add your Apple credentials
    echo.
) else (
    echo .env file already exists
    echo.
)

echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Edit .env file with your Apple credentials
echo 2. Run the validator:
echo    python validate_from_file.py receipt.txt "your_secret"
echo    python interactive_validator.py
echo.

pause
