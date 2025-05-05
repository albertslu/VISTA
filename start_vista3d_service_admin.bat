@echo off
cd /d C:\Users\Albert\VISTA
echo Starting VISTA3D Service with admin privileges at %date% %time%

:: Create service directories if they don't exist
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\tasks" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\tasks
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\processed" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\processed
if not exist "C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\failed" mkdir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D\failed

:: Start the VISTA3D service with Python
echo Running VISTA3D service...
python vista_service.py --base_dir C:\ARTDaemon\Segman\dcm2nifti\Tasks\Vista3D --interval 5

echo VISTA3D service exited with code %ERRORLEVEL%
pause
