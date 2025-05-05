@echo off
echo VISTA3D Test Suite
echo =================
echo.
echo This script will run a series of tests to verify VISTA3D functionality
echo.
echo Test Options:
echo 1. Basic point-based segmentation tests (liver, spleen, kidney)
echo 2. Full segmentation on sample CT scans
echo 3. Point-based liver segmentation on different CT scans
echo 4. Multiple organ segmentation on the same CT scan
echo 5. Run all tests
echo.

set /p CHOICE="Select test to run (1-5): "

if "%CHOICE%"=="1" (
    echo Running basic point-based segmentation tests...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\liver_test" --type point --point "175,136,141" --label 1
    echo Test complete! Check output\liver_test for results.
) else if "%CHOICE%"=="2" (
    echo Running full segmentation tests...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\full_test_s0031" --type full
    vista3d.exe infer --input "sample_data\s0052.nii.gz" --output "output\full_test_s0052" --type full
    echo Tests complete! Check output\full_test_* folders for results.
) else if "%CHOICE%"=="3" (
    echo Running point-based liver segmentation on different CT scans...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\liver_s0031" --type point --point "175,136,141" --label 1
    vista3d.exe infer --input "sample_data\s0052.nii.gz" --output "output\liver_s0052" --type point --point "175,136,141" --label 1
    echo Tests complete! Check output\liver_* folders for results.
) else if "%CHOICE%"=="4" (
    echo Running multiple organ segmentation on the same CT scan...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\spleen_s0031" --type point --point "215,108,141" --label 2
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\kidney_s0031" --type point --point "133,128,141" --label 3
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\pancreas_s0031" --type point --point "189,140,141" --label 7
    echo Tests complete! Check output\*_s0031 folders for results.
) else if "%CHOICE%"=="5" (
    echo Running all tests...
    
    echo 1. Basic point-based segmentation test (liver)...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\liver_test" --type point --point "175,136,141" --label 1
    
    echo 2. Full segmentation tests...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\full_test_s0031" --type full
    vista3d.exe infer --input "sample_data\s0052.nii.gz" --output "output\full_test_s0052" --type full
    
    echo 3. Point-based liver segmentation on different CT scans...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\liver_s0031" --type point --point "175,136,141" --label 1
    vista3d.exe infer --input "sample_data\s0052.nii.gz" --output "output\liver_s0052" --type point --point "175,136,141" --label 1
    
    echo 4. Multiple organ segmentation on the same CT scan...
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\spleen_s0031" --type point --point "215,108,141" --label 2
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\kidney_s0031" --type point --point "133,128,141" --label 3
    vista3d.exe infer --input "sample_data\s0031.nii.gz" --output "output\pancreas_s0031" --type point --point "189,140,141" --label 7
    
    echo All tests complete! Check output folder for results.
) else (
    echo Invalid choice. Please run the script again and select a number between 1 and 5.
)

echo.
pause
