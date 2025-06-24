# VISTA3D Medical Image Segmentation Service

## Quick Start

### 1. Start the Service (as Administrator)
```powershell
.\vista3d.exe service
```

### 2. Create a Task File
```json
{
  "task_id": "scan_001",
  "input_file": "C:/path/to/ct_scan.nii.gz",
  "output_directory": "C:/path/to/output/",
  "segmentation_type": "full"
}
```

### 3. Submit Task
- Drop the JSON file in the monitored folder
- Service automatically processes and generates segmentation

## Features
- ✅ 118 anatomical labels
- ✅ GPU acceleration (CUDA)
- ✅ Automatic monitoring
- ✅ Production ready

## Requirements
- Windows 10/11
- NVIDIA GPU (recommended)
- Administrator privileges

**For complete documentation, see VISTA3D_SERVICE_SETUP_GUIDE.md**
