@echo off
echo VISTA3D Batch Processing
echo =======================
echo.

REM Check if arguments are provided
if "%~1"=="" (
    echo Usage:
    echo   batch_process.bat [count] [type]
    echo.
    echo   count: Number of CT scans to process (default: 10)
    echo   type: Segmentation type - 'full' or 'point' (default: full)
    echo.
    echo Examples:
    echo   batch_process.bat 5 full
    echo   batch_process.bat 20 point
    echo.
    set /p COUNT="Enter number of scans to process (default 10): "
    set /p TYPE="Enter segmentation type (full/point, default full): "
) else (
    set COUNT=%1
    set TYPE=%2
)

if "%COUNT%"=="" set COUNT=10
if "%TYPE%"=="" set TYPE=full

echo.
echo Processing %COUNT% CT scans with %TYPE% segmentation...
echo.

REM Run the batch processing
vista3d.exe batch-process --count %COUNT% --type %TYPE%

echo.
echo Batch processing complete!
echo.
pause
