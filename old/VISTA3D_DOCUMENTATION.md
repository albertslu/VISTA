# VISTA3D Comprehensive Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
   - [From GitHub Repository](#from-github-repository)
   - [From Executable Package](#from-executable-package)
3. [Running VISTA3D](#running-vista3d)
   - [Command Line Mode](#command-line-mode)
   - [Service Mode](#service-mode)
4. [Task File Format](#task-file-format)
5. [Segmentation Modes](#segmentation-modes)
   - [Full Segmentation](#full-segmentation)
   - [Point-Based Segmentation](#point-based-segmentation)
   - [Specific Organ Segmentation](#specific-organ-segmentation)
6. [Common Organ Labels](#common-organ-labels)
7. [Troubleshooting](#troubleshooting)
8. [Examples](#examples)

## Introduction

VISTA3D (MONAI **V**ersatile **I**maging **S**egmen**T**ation and **A**nnotation) is a powerful tool for medical image segmentation that supports both automatic full-body segmentation and interactive point-based segmentation. This documentation provides comprehensive guidance on how to set up and use VISTA3D effectively.

## Installation

### From GitHub Repository

To install VISTA3D from the GitHub repository:

1. Clone the repository:
   ```bash
   git clone https://github.com/Project-MONAI/VISTA.git
   cd VISTA
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Download the model checkpoint:
   - Download from [Google Drive](https://drive.google.com/file/d/1DRYA2-AI-UJ23W1VbjqHsnHENGi0ShUl/view?usp=sharing)
   - Save it to `./vista3d/models/model.pt`

4. Build the executable (optional):
   ```bash
   python create_spec.py
   python create_installer.py
   pyinstaller vista3d.spec
   ```

### From Executable Package

If you have received the executable package:

1. Extract the `vista3d_executable.zip` file to a location of your choice
2. Open a command prompt as administrator
3. Navigate to the extracted folder
4. Run `setup.bat` to install VISTA3D as a Windows service (optional)

## Running VISTA3D

VISTA3D can be run in two primary modes: Command Line Mode and Service Mode.

### Command Line Mode

Command Line Mode is ideal for processing individual CT scans directly:

#### Full Segmentation

```bash
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
```

#### Point-Based Segmentation

```bash
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type point --point "x,y,z" --label label_number
```

Example for liver segmentation:
```bash
vista3d.exe infer --input "C:/CT_Scans/patient001.nii.gz" --output "C:/Segmentations/patient001_liver" --type point --point "175,136,141" --label 1
```

### Service Mode

Service Mode continuously monitors a folder for task files and processes them automatically:

1. Start the service:
   ```bash
   vista3d.exe service
   ```

   **Note:** When you first run the service, it automatically creates the necessary folder structure:
   ```
   vista_service/
   ├── tasks/        # Place task files here
   ├── processed/    # Successfully processed task files are moved here
   └── failed/       # Failed task files are moved here
   ```
   
   These folders are created in the same directory where the executable is located. You don't need to create them manually.

2. Create task files:
   ```bash
   vista3d.exe create-task --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
   ```
   
   Or for point-based segmentation:
   ```bash
   vista3d.exe create-task --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type point --point "x,y,z" --label label_number
   ```

   The task files are automatically placed in the `vista_service/tasks` folder.

3. Install as a Windows service (optional):
   ```bash
   vista3d.exe install-service
   ```
   
   This will create a Windows scheduled task that runs at system startup.

4. Uninstall the service:
   ```bash
   vista3d.exe uninstall-service
   ```

## Task File Format

Task files are JSON files that specify the segmentation parameters. They can be created manually or using the `create-task` command. Here's the format:

```json
{
  "task_id": "unique_task_identifier",
  "input_file": "path/to/ct_scan.nii.gz",
  "output_directory": "path/to/output_folder",
  "segmentation_type": "full",  // "full" or "point"
  "description": "Optional task description"
}
```

For point-based segmentation, add these fields:

```json
{
  "task_id": "liver_segmentation_001",
  "input_file": "path/to/ct_scan.nii.gz",
  "output_directory": "path/to/output_folder",
  "segmentation_type": "point",
  "point_coordinates": [175, 136, 141],  // [x, y, z]
  "label": 1,  // Organ label (1 = liver)
  "description": "Liver segmentation using point-based approach"
}
```

Alternative format (as requested):

```json
{
  "input": "image.nii.gz",
  "output": "outputs/label.nii.gz",
  "mode": "All",  // "All", ["Lung", "Brain"], or "Point"
  "point_coordinate": [100, 200, 125]  // Only required for "Point" mode
}
```

Task files should be placed in the `vista_service/tasks` directory. The service will automatically process them and move them to either `vista_service/processed` or `vista_service/failed` depending on the outcome.

## Segmentation Modes

VISTA3D supports multiple segmentation modes:

### Full Segmentation

Full segmentation (also called "All" mode) automatically segments all supported anatomical structures in the CT scan. This is the most comprehensive option but requires more processing time.

Command:
```bash
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type full
```

Task file:
```json
{
  "segmentation_type": "full"
}
```

Or with alternative format:
```json
{
  "mode": "All"
}
```

### Point-Based Segmentation

Point-based segmentation focuses on a specific location and organ label. This is faster and more targeted than full segmentation.

Command:
```bash
vista3d.exe infer --input "path/to/ct_scan.nii.gz" --output "path/to/output_folder" --type point --point "175,136,141" --label 1
```

Task file:
```json
{
  "segmentation_type": "point",
  "point_coordinates": [175, 136, 141],
  "label": 1
}
```

Or with alternative format:
```json
{
  "mode": "Point",
  "point_coordinate": [175, 136, 141],
  "label": 1
}
```

### Specific Organ Segmentation

You can also segment specific organs by providing a list of labels:

Task file:
```json
{
  "mode": ["Liver", "Spleen", "Kidney"]
}
```

Or using label numbers:
```json
{
  "segmentation_type": "specific",
  "label_prompt": [1, 2, 3, 4]
}
```

## Common Organ Labels

VISTA3D supports 127 different anatomical structures. Here are some common organ labels:

| Label | Organ Name      |
|-------|----------------|
| 1     | Liver          |
| 2     | Spleen         |
| 3     | Kidney (left)  |
| 4     | Kidney (right) |
| 7     | Pancreas       |
| 5     | Aorta          |
| 6     | Inferior vena cava |
| 8     | Adrenal gland  |
| 9     | Lung           |
| 10    | Brain          |

For a complete list of labels, refer to the `vista3d/data/jsons/label_dict.json` file.

## Troubleshooting

### Common Issues and Solutions

1. **CUDA errors**:
   - Make sure your NVIDIA drivers are up to date
   - Try running with `--device cpu` if GPU issues persist

2. **Memory errors**:
   - For large CT scans, try processing with a smaller batch size
   - Use point-based segmentation instead of full segmentation

3. **Service not starting**:
   - Check Windows Task Scheduler to ensure the service is properly registered
   - Verify that all paths in the configuration are correct

4. **Missing output files**:
   - Check the log files for errors
   - Ensure the output directory exists and is writable

5. **Slow processing**:
   - Point-based segmentation is much faster than full segmentation
   - Check if your system is using GPU acceleration

### Log Files

Check these log files for detailed error messages:
- `vista3d_cli.log` - Command line interface logs
- `vista_service.log` - Service mode logs

## Examples

### Example 1: Point-based Liver Segmentation

```bash
vista3d.exe infer --input "C:/CT_Scans/patient001.nii.gz" --output "C:/Segmentations/patient001_liver" --type point --point "175,136,141" --label 1
```

### Example 2: Full Segmentation

```bash
vista3d.exe infer --input "C:/CT_Scans/patient002.nii.gz" --output "C:/Segmentations/patient002_full" --type full
```

### Example 3: Creating a Task for the Service

```bash
vista3d.exe create-task --input "C:/CT_Scans/patient003.nii.gz" --output "C:/Segmentations/patient003_spleen" --type point --point "150,120,130" --label 2 --description "Spleen segmentation"
```

### Example 4: Batch Processing Multiple Scans

```bash
vista3d.exe batch-process --count 5 --type full
```

This will process 5 CT scans with full segmentation.

---

For additional support, please refer to the [MONAI Project](https://monai.io/) and [VISTA3D GitHub Repository](https://github.com/Project-MONAI/VISTA).
