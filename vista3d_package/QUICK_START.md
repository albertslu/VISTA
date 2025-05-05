<!--
Copyright (c) MONAI Consortium
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# MONAI VISTA Repository

This repository contains VISTA3D and VISTA2D, along with a service wrapper for automated medical image segmentation.

## VISTA3D Service

The VISTA3D Service is a wrapper around the VISTA3D segmentation framework that allows for automated batch processing of medical images. It monitors a designated folder for task files and processes them automatically.

### Features

- **Automated Processing**: Monitors a folder for task files and processes them automatically
- **Multiple Segmentation Modes**: Supports both point-based and full segmentation
- **Task Management**: Tracks task status and organizes results
- **Configurable**: Easy to configure through YAML files
- **Cross-Platform**: Works on Windows, Linux, and macOS

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/vista-service.git
   cd vista-service
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create necessary directories**:
   ```bash
   mkdir -p vista_service/tasks vista_service/processed vista_service/failed output
   ```

### Configuration

The service is configured through the `config.yaml` file. You can modify this file to change the service behavior:

- `service.base_directory`: Base directory for service files
- `service.check_interval`: Interval in seconds to check for new tasks
- `vista3d.device`: Device to use for inference ("auto", "cuda:0", "cpu", etc.)

### Usage

#### Starting the Service

```bash
# On Windows
python vista_service.py

# On Linux/macOS
python vista_service.py
```

#### Creating Tasks

Tasks are defined in JSON files placed in the `vista_service/tasks` folder. You can create them manually or use the provided utility:

```bash
# Full segmentation
python create_task.py --input "path/to/ct.nii.gz" --output "path/to/output" --type "full"

# Point-based segmentation
python create_task.py --input "path/to/ct.nii.gz" --output "path/to/output" --type "point" --point "175,136,141" --label 1
```

#### Task File Format

```json
{
    "task_id": "unique_task_id",
    "input_file": "path/to/ct.nii.gz",
    "output_directory": "path/to/output",
    "segmentation_type": "full",
    "description": "Optional description"
}
```

For point-based segmentation, add:
```json
{
    "point_coordinates": [175, 136, 141],
    "label": 1
}
```

### Running as a System Service

#### Windows

1. Use the provided batch file:
   ```
   start_vista_service.bat
   ```

2. Set up as a Task Scheduler task:
   - Open Task Scheduler
   - Create a new task with trigger "At startup"
   - Action: Start a program
   - Program/script: `path\to\start_vista_service.bat`

#### Linux

1. Create a systemd service:
   ```bash
   sudo nano /etc/systemd/system/vista3d.service
   ```

2. Add the following content:
   ```
   [Unit]
   Description=VISTA3D Segmentation Service
   After=network.target

   [Service]
   User=yourusername
   WorkingDirectory=/path/to/vista-service
   ExecStart=/usr/bin/python3 vista_service.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable vista3d.service
   sudo systemctl start vista3d.service
   ```

### Batch Processing

For batch processing of multiple CT scans, use the provided scripts:

```bash
# Process specific scans
python process_s50_to_s60.py

# Process random subset of scans
python batch_process_totalsegmentator.py --count 100
```

## Troubleshooting

- **CUDA Issues**: If you encounter CUDA errors, check that your PyTorch installation matches your CUDA version
- **Memory Errors**: For large CT scans, try using the memory-efficient mode in the config
- **Task Not Processing**: Check the service log file for errors

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
