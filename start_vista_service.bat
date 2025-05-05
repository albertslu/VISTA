@echo off
echo Starting VISTA3D Service at %date% %time% >> C:\Users\Albert\VISTA\service_startup.log

:: Set the working directory
cd /d C:\Users\Albert\VISTA

:: Create service directories if they don't exist
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\tasks" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\tasks
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\processed" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\processed
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\failed" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\failed

:: Check if Python is in PATH
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH at %date% %time% >> C:\Users\Albert\VISTA\service_startup.log
    exit /b 1
)

:: Start the VISTA3D service with the full path to the config file
echo Running VISTA3D service... >> C:\Users\Albert\VISTA\service_startup.log
start /B C:\Users\Albert\VISTA\vista3d_package\vista3d.exe service --base_dir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D --interval 30 --config C:\Users\Albert\VISTA\vista3d_package\config.yaml >> C:\Users\Albert\VISTA\service_output.log 2>&1

echo VISTA3D service started successfully at %date% %time% >> C:\Users\Albert\VISTA\service_startup.log
exit /b 0
