@echo off
setlocal enabledelayedexpansion

:: Clear PYTHONPATH and PYTHONHOME to prevent Python 3 from loading Python 2.7 site-packages
set PYTHONPATH=
set PYTHONHOME=

set "PYTHON_BIN="

:: Scan PATH for python executables
for /f "delims=" %%I in ('where python 2^>nul') do (
    if not defined PYTHON_BIN (
        "%%I" -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_BIN=%%I"
        )
    )
)

:: Try standard 'py' launcher if python was not found or was not Python 3
if not defined PYTHON_BIN (
    py -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_BIN=py"
    )
)

:: If still not found, check standard installation paths
if not defined PYTHON_BIN (
    if exist "C:\Program Files\Python312\python.exe" (
        set "PYTHON_BIN=C:\Program Files\Python312\python.exe"
    )
)

if not defined PYTHON_BIN (
    echo [ERROR] Python 3 was not found on your system.
    echo Please install Python 3.12 or newer.
    pause
    exit /b 1
)

echo Starting Log Diagnostic ^& RCA Hub local server...
echo Using Python interpreter: !PYTHON_BIN!
echo Checking dependencies...

"!PYTHON_BIN!" -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [WARNING] Failed to automatically run pip install. Attempting to start server anyway...
)

echo Launching application runner script...
"!PYTHON_BIN!" run.py
pause
