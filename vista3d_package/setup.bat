@echo off 
echo Setting up VISTA3D... 
 
REM Create necessary directories 
mkdir vista_service\tasks 2>nul 
mkdir vista_service\processed 2>nul 
mkdir vista_service\failed 2>nul 
mkdir output 2>nul 
 
REM Install as a service 
echo Installing VISTA3D as a Windows service... 
schtasks /create /tn "VISTA3D_Service" /tr "%~dp0vista3d.exe service" /sc onstart /ru SYSTEM /f 
 
echo Setup complete! 
echo You can now use VISTA3D with the following commands: 
echo   vista3d.exe infer --input "path\to\ct_scan.nii.gz" --output "path\to\output_folder" --type full 
echo   vista3d.exe infer --input "path\to\ct_scan.nii.gz" --output "path\to\output_folder" --type point --point "175,136,141" --label 1 
echo   vista3d.exe service 
 
pause 
