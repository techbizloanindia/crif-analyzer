@echo off
setlocal enabledelayedexpansion
title CRIF High Mark Credit Analyzer

REM Always run from the folder this script lives in
cd /d "%~dp0"

echo ===============================================
echo    CRIF High Mark Credit Analyzer
echo ===============================================
echo.

REM ---------------------------------------------------------------
REM  Step 0 : Make sure Python is available
REM ---------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on this system.
    echo.
    echo Please install Python 3.9 or newer from:
    echo     https://www.python.org/downloads/
    echo During setup, tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo Using Python !PYVER!
echo.

REM ---------------------------------------------------------------
REM  Step 1 : Check for required modules, auto-install if missing
REM ---------------------------------------------------------------
echo [1/2] Checking required modules...
python -c "import streamlit, pdfplumber, pandas, openpyxl, plotly, xlsxwriter" >nul 2>&1
if errorlevel 1 (
    echo       Missing modules detected - installing dependencies...
    echo.
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed.
        echo Check your internet connection and try again.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo       Dependencies installed successfully.
) else (
    echo       All required modules are already installed.
)

echo.
REM ---------------------------------------------------------------
REM  Step 2 : Launch the Streamlit app
REM ---------------------------------------------------------------
echo [2/2] Starting the app...
echo.
echo   The app will open in your browser at: http://localhost:8501
echo   Login    Username: crif.analyzer
echo            Password: Credit.team@analyzer
echo.
echo   Keep this window open while using the app.
echo   Press Ctrl+C here to stop the app.
echo.

python -m streamlit run app.py

echo.
echo App stopped.
pause
endlocal
