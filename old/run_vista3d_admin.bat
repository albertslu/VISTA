@echo off
cd /d C:\Users\Albert\VISTA
echo Starting VISTA3D Service with admin privileges at %date% %time%

:: Create service directories if they don't exist
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\tasks" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\tasks
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\processed" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\processed
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\failed" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\failed

:: Start the VISTA3D service with the full path to the config file
echo Running VISTA3D service...
C:\Users\Albert\VISTA\vista3d_package\vista3d.exe service --base_dir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D --interval 5 --config C:\Users\Albert\VISTA\vista3d_package\config.yaml

echo VISTA3D service exited with code %ERRORLEVEL%
pause
