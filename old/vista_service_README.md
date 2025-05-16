# VISTA3D Service Wrapper

This service wrapper allows you to run VISTA3D medical image segmentation tasks automatically by simply placing task files in a monitored folder.

## Overview

The service consists of three main components:

1. **VISTA Service (`vista_service.py`)**: A daemon that monitors a folder for task files and processes them automatically
2. **Task Creator (`create_task.py`)**: A utility to easily create properly formatted task files
3. **Task Template (`task_template.json`)**: An example of the task file format

## Folder Structure

When you run the service, it creates the following folder structure:

```
vista_service/
├── tasks/        # Place new task files here
├── processed/    # Successfully processed task files are moved here
└── failed/       # Failed task files are moved here
```

## Task File Format

Task files are JSON files with the following structure:

```json
{
    "task_id": "liver_segmentation_001",
    "input_file": "C:/path/to/ct.nii.gz",
    "output_directory": "C:/path/to/output",
    "segmentation_type": "point",
    "point_coordinates": [175, 136, 141],
    "label": 1,
    "description": "Liver segmentation using point-based approach"
}
```

For full segmentation (all anatomical structures), omit the `point_coordinates` and `label` fields and set `segmentation_type` to `"full"`.

## How to Use

### 1. Start the Service

Start the VISTA3D service to monitor for new tasks:

```bash
python vista_service.py --base_dir ./vista_service --interval 30
```

Parameters:
- `--base_dir`: Base directory for the service (default: `./vista_service`)
- `--interval`: Polling interval in seconds (default: 30)

### 2. Create Tasks

#### Using the Task Creator

```bash
# For point-based segmentation
python create_task.py --input "C:/path/to/ct.nii.gz" --output "C:/path/to/output" --type "point" --point "175,136,141" --label 1

# For full segmentation
python create_task.py --input "C:/path/to/ct.nii.gz" --output "C:/path/to/output" --type "full"
```

Parameters:
- `--task_id`: Unique task identifier (generated automatically if not provided)
- `--input`: Input CT scan file (required)
- `--output`: Output directory for segmentation results (required)
- `--type`: Segmentation type (`full` or `point`)
- `--point`: Point coordinates (x,y,z) for point-based segmentation
- `--label`: Label for point-based segmentation
- `--description`: Task description
- `--tasks_dir`: Directory to save task files (default: `./vista_service/tasks`)

#### Manually Creating Task Files

You can also manually create JSON task files and place them in the `tasks` directory.

### 3. Monitor Results

Each processed task will create:
- The segmentation output in the specified output directory
- A result JSON file with processing information

## Example Workflow

1. Start the service:
   ```bash
   python vista_service.py
   ```

2. Create a point-based segmentation task for the liver:
   ```bash
   python create_task.py --input "C:/Users/Albert/Totalsegmentator_dataset_v201/s0031/ct.nii.gz" --output "C:/Users/Albert/output/liver_seg_001" --type "point" --point "175,136,141" --label 1 --description "Liver segmentation"
   ```

3. The service will automatically:
   - Detect the new task file
   - Run the VISTA3D segmentation
   - Save the results to the specified output directory
   - Move the task file to the `processed` folder

4. Check the results in your output directory

## Common Labels

- 1: Liver
- 3: Spleen
- 4: Pancreas
- 5: Right Kidney
- 6: Aorta

For a complete list of labels, refer to the `vista3d/data/jsons/label_dict.json` file.

## Troubleshooting

- Check the `vista_service.log` file for detailed logs
- Failed tasks are moved to the `failed` directory with error information
- Each task creates a result JSON file with success/failure information
