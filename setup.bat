@echo off
echo VISTA3D Setup
echo ==============
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Error: This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo Setting up VISTA3D...

REM Create necessary directories
if not exist "vista_service\tasks" mkdir "vista_service\tasks"
if not exist "vista_service\processed" mkdir "vista_service\processed"
if not exist "vista_service\failed" mkdir "vista_service\failed"
if not exist "output" mkdir "output"

echo Directories created.
echo.

REM Install as a service
echo Installing VISTA3D as a service...
vista3d.exe install-service
if %errorLevel% neq 0 (
    echo Failed to install service.
    pause
    exit /b 1
)

echo.
echo Setup complete!
echo.
echo VISTA3D has been installed as a Windows service.
echo It will start automatically when the system boots.
echo.
echo Usage:
echo   vista3d.exe infer --input "path/to/ct.nii.gz" --output "path/to/output" --type full
echo   vista3d.exe service
echo   vista3d.exe create-task --input "path/to/ct.nii.gz" --output "path/to/output" --type full
echo.
pause
