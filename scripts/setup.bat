@echo off
echo ===================================================
echo             AgentForge Setup Installer
echo ===================================================
echo Checking dependencies...

:: Check python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.11+.
    exit /b 1
) else (
    echo [OK] Python detected.
)

:: Check node
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH. Please install Node 18+.
    exit /b 1
) else (
    echo [OK] Node.js detected.
)

:: Setup python venv in backend
echo.
echo Setting up Python virtual environment...
cd %~dp0\..\backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
echo Installing Backend dependencies...
pip install -r requirements.txt
call venv\Scripts\deactivate

:: Setup npm in frontend
echo.
echo Installing Frontend NPM dependencies...
cd %~dp0\..\frontend
call npm install

echo.
echo ===================================================
echo Setup complete!
echo To run backend: cd backend ^& venv\Scripts\activate ^& uvicorn app.main:app --reload
echo To run frontend: cd frontend ^& npm run dev
echo ===================================================
pause
