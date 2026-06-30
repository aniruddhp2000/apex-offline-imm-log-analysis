@echo off
echo Starting Log Diagnostic & RCA Hub local server...
echo Checking dependencies...
py -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies. Make sure Python is in your PATH.
    pause
    exit /b
)
echo Opening browser on http://localhost:8000/ ...
start http://localhost:8000/
echo Launching Uvicorn server on http://localhost:8000/ ...
py -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
pause
