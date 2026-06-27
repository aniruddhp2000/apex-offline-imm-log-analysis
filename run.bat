@echo off
echo Starting Log Diagnostic & RCA Hub local server...
echo Checking dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies. Make sure Python is in your PATH.
    pause
    exit /b
)
echo Launching Uvicorn server on http://localhost:8000/ ...
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
pause
