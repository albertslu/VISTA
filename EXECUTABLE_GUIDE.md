# VISTA3D Executable Guide

This guide explains how to build, distribute, set up, and use the VISTA3D executable package for CT scan segmentation.

## Building the VISTA3D Executable from Source

### Prerequisites

- Windows 10 or 11 (64-bit)
- CUDA-capable NVIDIA GPU (recommended: at least 8GB VRAM)
- CUDA Toolkit 11.7 or newer
- Python 3.8 or newer
- PyInstaller (`pip install pyinstaller`)

### Step 1: Set Up the Environment

1. Clone the VISTA repository or use your existing copy:
   ```
   git clone https://github.com/Project-MONAI/VISTA.git
   cd VISTA/vista3d
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv vista3d_env
   vista3d_env\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   pip install pyinstaller
   ```

4. Download the model checkpoint from [Google Drive](https://drive.google.com/file/d/1DRYA2-AI-UJ23W1VbjqHsnHENGi0ShUl/view?usp=sharing) and save it to `models/model.pt`

### Step 2: Use the Existing CLI Wrapper

You already have the `vista3d_cli.py` file, which serves as the command-line interface for VISTA3D. This script handles:

- Direct inference on CT scans
- Service mode for continuous processing
- Task creation for the service
- Windows service installation/uninstallation

### Step 3: Build the Executable

1. Create a PyInstaller spec file named `vista3d.spec` if you don't already have one:
   ```python
   # -*- mode: python ; coding: utf-8 -*-

   block_cipher = None

   a = Analysis(
       ['vista3d_cli.py'],
       pathex=[],
       binaries=[],
       datas=[
           ('configs', 'configs'),
           ('models/model.pt', 'models'),
           ('data/jsons/label_dict.json', 'data/jsons'),
           ('data/jsons/label_mappings.json', 'data/jsons'),
       ],
       hiddenimports=[
           'torch',
           'torchvision',
           'monai',
           'nibabel',
           'numpy',
           'scipy',
           'skimage',
           'PIL',
           'yaml',
           'json',
       ],
       hookspath=[],
       hooksconfig={},
       runtime_hooks=[],
       excludes=[],
       win_no_prefer_redirects=False,
       win_private_assemblies=False,
       cipher=block_cipher,
       noarchive=False,
   )

   pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

   exe = EXE(
       pyz,
       a.scripts,
       [],
       exclude_binaries=True,
       name='vista3d',
       debug=False,
       bootloader_ignore_signals=False,
       strip=False,
       upx=True,
       console=True,
       disable_windowed_traceback=False,
       argv_emulation=False,
       target_arch=None,
       codesign_identity=None,
       entitlements_file=None,
   )

   coll = COLLECT(
       exe,
       a.binaries,
       a.zipfiles,
       a.datas,
       strip=False,
       upx=True,
       upx_exclude=[],
       name='vista3d',
   )
   ```

2. Build the executable using PyInstaller:
   ```
   pyinstaller --clean vista3d.spec
   ```

3. This will create a `dist/vista3d` directory containing the executable and all necessary dependencies.

### Step 4: Create Supporting Files

1. Create a `setup.bat` file in the `dist/vista3d` directory:
   ```batch
   @echo off
   echo Installing VISTA3D as a Windows service...

   REM Check for administrator privileges
   net session >nul 2>&1
   if %errorLevel% neq 0 (
       echo This script requires administrator privileges.
       echo Please run as administrator.
       pause
       exit /b 1
   )

   REM Create task directories
   mkdir "%~dp0vista_service\tasks" 2>nul
   mkdir "%~dp0vista_service\processed" 2>nul
   mkdir "%~dp0vista_service\failed" 2>nul

   REM Install as a service
   "%~dp0vista3d.exe" install-service

   echo.
   echo VISTA3D service installation completed.
   echo.

   pause
   ```

2. Create a `batch_process.bat` file for batch processing:
   ```batch
   @echo off
   setlocal enabledelayedexpansion

   REM Check if number of scans is provided
   if "%1"=="" (
       set NUM_SCANS=10
   ) else (
       set NUM_SCANS=%1
   )

   REM Check if segmentation type is provided
   if "%2"=="" (
       set SEG_TYPE=full
   ) else (
       set SEG_TYPE=%2
   )

   echo Processing %NUM_SCANS% scans with %SEG_TYPE% segmentation...

   REM Call the Python script for batch processing
   "%~dp0vista3d.exe" batch-process --num_scans %NUM_SCANS% --type %SEG_TYPE%

   echo.
   echo Batch processing completed.
   echo.

   pause
   ```

### Step 5: Package the Executable

Create a ZIP file containing the entire `dist/vista3d` directory:

```
powershell Compress-Archive -Path dist/vista3d/* -DestinationPath vista3d_executable.zip
```

## For Users (Your Coworkers)

### Downloading and Installing

1. Obtain the `vista3d_executable.zip` file from your distribution method (file share, email, etc.)
2. Extract the zip file to a location of your choice
3. Open a command prompt as administrator
4. Navigate to the extracted folder
5. Run `setup.bat` to install VISTA3D as a Windows service (optional)

### Using VISTA3D

#### Direct Inference Mode

For quick segmentation of a single CT scan:

```
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
```

For point-based segmentation (e.g., for liver - label 1):

```
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type point --point "175,136,141" --label 1
```

#### Service Mode

Start the service manually:

```
vista3d.exe service
```

Create tasks for the service:

```
vista3d.exe create-task --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
```

#### Batch Processing

Process multiple scans at once:

```
batch_process.bat [number_of_scans] [segmentation_type]
```

### Task File Format

When using the service mode, task files should be JSON files with the following structure:

```json
{
  "task_id": "unique_task_id",
  "input_file": "path/to/input.nii.gz",
  "output_file": "path/to/output.nii.gz",
  "output_directory": "path/to/output_folder",
  "segmentation_type": "point",
  "point": "175,136,141",
  "label": 1
}
```

## Examples

### Example 1: Point-based Segmentation of Liver

```
vista3d.exe infer --input "C:\CT_Scans\patient001.nii.gz" --output "C:\Segmentations\patient001_liver" --type point --point "175,136,141" --label 1
```

### Example 2: Full Segmentation of Multiple Scans

```
batch_process.bat 5 full
```

### Example 3: Creating a Task for the Service

```
vista3d.exe create-task --input "C:\CT_Scans\patient002.nii.gz" --output "C:\Segmentations\patient002_full" --type full
```

## Performance Considerations

- VISTA3D performs best on systems with NVIDIA GPUs
- For large CT scans, ensure you have at least 16GB of RAM
- Processing time varies based on segmentation type:
  - Point-based: ~30 seconds per scan
  - Full: ~2-5 minutes per scan

## Additional Resources

- [MONAI Project](https://monai.io/)
- [VISTA3D GitHub Repository](https://github.com/Project-MONAI/VISTA)
- [NIfTI File Format](https://nifti.nimh.nih.gov/)

## Troubleshooting

- If you encounter "DLL not found" errors, make sure all required CUDA DLLs are in the system PATH
- If you face memory issues, try reducing the batch size in the configuration files
- For CUDA compatibility issues, ensure you're using a compatible version of PyTorch and CUDA
- Check the log file (`vista3d_cli.log`) for detailed error messages
