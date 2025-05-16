@echo off
cd /d C:\Users\Albert\VISTA
echo Running VISTA3D inference with admin privileges at %date% %time%

:: Create output directory if it doesn't exist
if not exist "C:\ARTDaemon\Segman\dcm2nifti\GGJJVZPCBPSSDVRV\MR.1.3.12.2.1107.5.2.43.66059.9420413823708647.0.0.0\Vista3D" mkdir "C:\ARTDaemon\Segman\dcm2nifti\GGJJVZPCBPSSDVRV\MR.1.3.12.2.1107.5.2.43.66059.9420413823708647.0.0.0\Vista3D"

:: Run the VISTA3D inference directly
echo Running VISTA3D inference...
C:\Users\Albert\VISTA\vista3d_package\vista3d.exe infer --input "C:\ARTDaemon\Segman\dcm2nifti\GGJJVZPCBPSSDVRV\MR.1.3.12.2.1107.5.2.43.66059.9420413823708647.0.0.0\image.nii.gz" --output "C:\ARTDaemon\Segman\dcm2nifti\GGJJVZPCBPSSDVRV\MR.1.3.12.2.1107.5.2.43.66059.9420413823708647.0.0.0\Vista3D\segmentation.nii.gz" --type full --config C:\Users\Albert\VISTA\vista3d_package\config.yaml

echo VISTA3D inference exited with code %ERRORLEVEL%
pause
