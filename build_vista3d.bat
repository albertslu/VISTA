@echo off
echo Building VISTA3D Installer
echo ========================
echo.

REM Create the one-file executable
pyinstaller --onefile --clean --name vista3d ^
  --add-data "vista3d;vista3d" ^
  --add-data "config.yaml;." ^
  --add-data "vista3d\configs\infer.yaml;vista3d\configs" ^
  --add-data "vista3d\configs\*.yaml;vista3d\configs" ^
  --hidden-import torch ^
  --hidden-import monai ^
  --hidden-import nibabel ^
  --hidden-import yaml ^
  --hidden-import numpy ^
  --hidden-import vista3d.scripts.infer ^
  --hidden-import vista3d.modeling ^
  --uac-admin ^
  vista3d_cli.py

echo.
echo Build complete!
echo The executable is available at: dist\vista3d.exe
echo.

REM Create installation directory structure
mkdir vista3d_package
mkdir vista3d_package\sample_data
mkdir vista3d_package\output

REM Copy the executable and other files
copy dist\vista3d.exe vista3d_package\
copy setup.bat vista3d_package\
copy README.md vista3d_package\QUICK_START.md
copy config.yaml vista3d_package\
mkdir vista3d_package\vista3d\configs
copy vista3d\configs\infer.yaml vista3d_package\vista3d\configs\

echo Creating setup.bat in the package...
echo @echo off > vista3d_package\setup.bat
echo echo Setting up VISTA3D... >> vista3d_package\setup.bat
echo. >> vista3d_package\setup.bat
echo REM Create necessary directories >> vista3d_package\setup.bat
echo mkdir vista_service\tasks 2^>nul >> vista3d_package\setup.bat
echo mkdir vista_service\processed 2^>nul >> vista3d_package\setup.bat
echo mkdir vista_service\failed 2^>nul >> vista3d_package\setup.bat
echo mkdir output 2^>nul >> vista3d_package\setup.bat
echo. >> vista3d_package\setup.bat
echo REM Install as a service >> vista3d_package\setup.bat
echo echo Installing VISTA3D as a Windows service... >> vista3d_package\setup.bat
echo schtasks /create /tn "VISTA3D_Service" /tr "%%~dp0vista3d.exe service" /sc onstart /ru SYSTEM /f >> vista3d_package\setup.bat
echo. >> vista3d_package\setup.bat
echo echo Setup complete! >> vista3d_package\setup.bat
echo echo You can now use VISTA3D with the following commands: >> vista3d_package\setup.bat
echo echo   vista3d.exe infer --input "path\to\ct_scan.nii.gz" --output "path\to\output_folder" --type full >> vista3d_package\setup.bat
echo echo   vista3d.exe infer --input "path\to\ct_scan.nii.gz" --output "path\to\output_folder" --type point --point "175,136,141" --label 1 >> vista3d_package\setup.bat
echo echo   vista3d.exe service >> vista3d_package\setup.bat
echo. >> vista3d_package\setup.bat
echo pause >> vista3d_package\setup.bat

echo.
echo Package created in vista3d_package folder!
echo You can now distribute this folder to your coworkers.
echo.
pause
