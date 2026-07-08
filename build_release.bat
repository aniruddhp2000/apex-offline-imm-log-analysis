@echo off
echo ==========================================
echo APex RCA Utility - Build & Release Pipeline
echo ==========================================

echo [1/3] Cleaning previous builds...
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q release
mkdir release

echo [2/3] Compiling Core Application (APex_RCA_Core.exe)...
pyinstaller --clean APex_RCA_Service.spec
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile APex_RCA_Core.
    exit /b 1
)

echo [3/3] Compiling GUI Installer (APex_RCA_Setup_v1.0.exe)...
pyinstaller --clean APex_RCA_Setup.spec
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile APex_RCA_Setup.
    exit /b 1
)

echo Moving final setup executable to release folder...
move dist\APex_RCA_Setup_v1.0.exe release\

echo.
echo ==========================================
echo Build Pipeline Complete!
echo The installer is located in: release\APex_RCA_Setup_v1.0.exe
echo ==========================================
pause
