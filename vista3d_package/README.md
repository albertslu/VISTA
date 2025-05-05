# VISTA3D Executable Package

This package contains a standalone executable version of the VISTA3D segmentation tool, which can perform both point-based and full segmentation on CT scans.

## Installation

1. Extract this package to a location of your choice
2. Run `setup.bat` as administrator to install VISTA3D as a Windows service (optional)

## Usage

VISTA3D can be used in two modes:

### Direct Inference Mode

```
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
```

For point-based segmentation (e.g., for liver - label 1):

```
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type point --point "175,136,141" --label 1
```

### Service Mode

Start the service manually:

```
vista3d.exe service
```

Create tasks for the service:

```
vista3d.exe create-task --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
```

### Service Installation/Uninstallation

Install as a Windows service:

```
vista3d.exe install-service
```

Uninstall the Windows service:

```
vista3d.exe uninstall-service
```

## Common Label IDs

- 1: Liver
- 2: Spleen
- 3: Kidney (left)
- 4: Kidney (right)
- 7: Pancreas

## Troubleshooting

- If you encounter CUDA errors, make sure your NVIDIA drivers are up to date
- For memory errors with large CT scans, try processing with a smaller batch size
- Check the log file (`vista3d_cli.log`) for detailed error messages
