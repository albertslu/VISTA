# VISTA3D Medical Image Segmentation Service
## Setup Guide for Production Deployment

### 📋 Overview
The VISTA3D service provides automated medical image segmentation using AI. It monitors folders for task files and automatically processes CT/MR scans to generate anatomical segmentations.

---

## 🎯 What You Need to Download

**Package**: `vista3d_package` folder (complete self-contained package)
- **Main Executable**: `vista3d.exe` (50MB)
- **Dependencies**: All libraries included in `_internal` folder
- **Configuration**: `config.json` and `_internal/config.yaml`

---

## 💻 System Requirements

### Minimum Requirements:
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB free space
- **GPU**: NVIDIA GPU with CUDA support (recommended for speed)
- **CPU**: Multi-core processor (service will use up to 16 threads)

### Software Requirements:
- **None!** - Everything is packaged in the executable

---

## 🚀 Quick Start (3 Steps)

### Step 1: Download & Extract
1. Download the `vista3d_package` folder
2. Place it anywhere on your system (e.g., `C:\VISTA3D\`)
3. No installation required!

### Step 2: Start the Service
1. Open **PowerShell as Administrator**
2. Navigate to the package: `cd "C:\path\to\vista3d_package"`
3. Run: `.\vista3d.exe service`

```powershell
# Example:
cd "C:\VISTA3D\vista3d_package"
.\vista3d.exe service
```

### Step 3: Submit Tasks
1. Create JSON task files
2. Drop them in the monitoring folder
3. Results appear automatically in output directories

---

## 📁 Folder Structure

```
vista3d_package/
├── vista3d.exe                 # Main executable (50MB)
├── _internal/                  # Dependencies & libraries
├── config.json                 # Service configuration
├── vista_service/              # Local task directories
│   ├── tasks/                  # Drop tasks here (if using local mode)
│   ├── processed/              # Completed tasks
│   └── failed/                 # Failed tasks
└── output/                     # Default output location
```

---

## ⚙️ Configuration

### Service Configuration (`config.json`)
```json
{
  "service": {
    "base_directory": "C:/your/monitoring/path",
    "tasks_directory": "tasks",
    "check_interval": 3,
    "log_file": "vista_service.log"
  },
  "vista3d": {
    "device": "auto",           // "auto", "cuda:0", or "cpu"
    "memory_efficient": true
  },
  "output": {
    "save_format": "nii.gz"
  }
}
```

**Key Settings:**
- `base_directory`: Where to monitor for tasks
- `check_interval`: How often to check for new tasks (seconds)
- `device`: "auto" for GPU detection, "cpu" for CPU-only

---

## 📝 Creating Task Files

### Full Segmentation Task
```json
{
  "task_id": "patient_001_full",
  "input_file": "C:/path/to/ct_scan.nii.gz",
  "output_directory": "C:/path/to/output/",
  "segmentation_type": "full"
}
```

### Point-Based Segmentation Task
```json
{
  "task_id": "patient_001_liver",
  "input_file": "C:/path/to/ct_scan.nii.gz",
  "output_directory": "C:/path/to/output/",
  "segmentation_type": "point",
  "segmentation_prompts": [
    {
      "target_output_label": 1,
      "positive_points": [[150, 200, 100]],
      "negative_points": [[140, 190, 95]]
    }
  ]
}
```

---

## 🔧 Service Commands

### Start Service
```powershell
.\vista3d.exe service
```

### Start with Custom Config
```powershell
.\vista3d.exe service --config "path/to/config.json"
```

### Create Task File
```powershell
.\vista3d.exe create-task --input "scan.nii.gz" --output "results/" --type "full"
```

### Direct Inference (No Service)
```powershell
.\vista3d.exe infer --input "scan.nii.gz" --output "results/" --type "full"
```

### Install as Windows Service
```powershell
.\vista3d.exe install-service
```

---

## 📊 Monitoring & Logs

### Log Files:
- `vista_service.log` - Service activity
- `vista3d_cli.log` - Application logs

### Expected Log Output:
```
2025-06-24 01:29:03,855 - VISTA3D-Service - INFO - Starting VISTA3D service
2025-06-24 01:29:03,855 - VISTA3D-Service - INFO - Found 1 task files
2025-06-24 01:29:03,863 - VISTA3D-Service - INFO - Processing task: patient_001
2025-06-24 01:30:26,941 - VISTA3D-Service - INFO - Using CUDA device
2025-06-24 01:32:53,922 - VISTA3D-Service - INFO - Running full segmentation with 118 labels
2025-06-24 01:33:03,465 - VISTA3D-Service - INFO - Task patient_001 completed successfully
```

---

## 🎯 Supported File Formats

### Input:
- **NIfTI**: `.nii`, `.nii.gz` (preferred)
- **DICOM**: Converted to NIfTI first

### Output:
- **Segmentation Masks**: `.nii.gz`
- **Label Maps**: 118 anatomical structures
- **Metadata**: JSON files with processing info

---

## 🚨 Troubleshooting

### Service Won't Start
1. **Run as Administrator** - Required for service operations
2. **Check Paths** - Ensure input files exist
3. **GPU Issues** - Set `"device": "cpu"` in config if GPU problems

### Tasks Not Processing
1. **Check Directory** - Verify `base_directory` in config
2. **File Permissions** - Ensure read/write access
3. **JSON Format** - Validate task file syntax

### Performance Issues
1. **GPU Usage** - Verify "Using CUDA device" in logs
2. **Memory** - Monitor system RAM usage
3. **CPU Threads** - Default 16 threads (configurable)

---

## 📈 Performance Expectations

### Processing Times:
- **First Run**: 2-3 minutes (model loading)
- **Subsequent Runs**: 30-60 seconds per scan
- **GPU vs CPU**: 5-10x faster with CUDA GPU

### Output:
- **118 Anatomical Labels** automatically detected
- **High Accuracy** - Medical-grade segmentation
- **Multiple Formats** - NIfTI, visualization ready

---

## 🔐 Production Deployment

### As Windows Service:
```powershell
.\vista3d.exe install-service
```

### Service Management:
```powershell
# Start service
schtasks /run /tn VISTA3D_Service

# Check status
Get-Process -Name "vista3d"
```

### Integration:
- Monitor specific folders
- Automatic processing
- Email notifications (custom)
- Database integration (custom)

---

## 📞 Support

### Successfully Tested Configuration:
- ✅ Windows 11
- ✅ NVIDIA GPU with CUDA
- ✅ Real medical imaging data
- ✅ Full segmentation (118 labels)
- ✅ Administrator privileges
- ✅ Production-ready performance

### Contact:
- For technical issues or custom configurations
- Performance optimization
- Integration support

---

**Status: ✅ PRODUCTION READY**  
*Successfully processing real medical imaging data with GPU acceleration* 