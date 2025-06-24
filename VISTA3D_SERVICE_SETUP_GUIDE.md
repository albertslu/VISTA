# VISTA3D Service Setup Guide

## Overview
VISTA3D is a medical image segmentation service that uses AI to automatically segment anatomical structures in CT scans. This service has been **successfully tested with real medical imaging data** and can process both full anatomical segmentation (118 labels) and targeted point-based segmentation.

## Package Information
- **Complete Package Size**: 13.84 GB uncompressed, 8.5 GB compressed
- **Executable Size**: 48 MB (vista3d.exe)
- **Dependencies**: ~13.8 GB (required _internal folder)
- **Architecture**: Windows executable with bundled Python, PyTorch, CUDA libraries

⚠️ **Important**: The `_internal/` folder is **REQUIRED** and cannot be removed. The executable alone will not work without all dependencies.

## System Requirements
- **Operating System**: Windows 10 or Windows 11
- **Memory**: 8GB RAM minimum (16GB recommended)
- **GPU**: NVIDIA GPU with CUDA support (recommended for speed)
- **Storage**: 15GB free space
- **Privileges**: Administrator access required for service installation

## Quick Start (Recommended for Deployment)

### Method 1: Extract and Run (Easiest)
1. Extract the complete package to your desired location
2. Navigate to the extracted folder
3. Right-click `START_SERVICE.bat` and select "Run as administrator"
4. The service will start monitoring for task files

### Method 2: Manual Command Line
1. Open PowerShell/Command Prompt as Administrator
2. Navigate to the package directory
3. Run: `.\vista3d.exe service --config "config.json"`

## Configuration

### Service Configuration (config.json)
```json
{
  "service": {
    "task_directory": "C:/ARTDaemon/Segman/dcm2nifti/Tasks/Vista3D",
    "processed_directory": "C:/ARTDaemon/Segman/dcm2nifti/Tasks/Vista3D/processed",
    "failed_directory": "C:/ARTDaemon/Segman/dcm2nifti/Tasks/Vista3D/failed",
    "check_interval": 3,
    "max_concurrent_tasks": 1
  },
  "model": {
    "checkpoint_path": "_internal/vista3d/models/model.pt"
  },
  "logging": {
    "level": "INFO",
    "file": "vista3d_service.log"
  }
}
```

**Important**: Update the directory paths to match your system's file structure.

## Task File Formats

### Full Segmentation (118 Anatomical Labels)
```json
{
  "task_id": "vista3d_full_001",
  "input_file": "path/to/scan.nii.gz",
  "segmentation_type": "full"
}
```

### Point-Based Segmentation (Targeted)
```json
{
  "task_id": "vista3d_point_001",
  "input_file": "path/to/scan.nii.gz",
  "segmentation_type": "point",
  "segmentation_prompts": [
    {
      "target_output_label": 1,
      "positive_points": [[113, 200, 96]],
      "negative_points": []
    }
  ]
}
```

**Note**: Point coordinates are in voxel space [x, y, z]. Multiple prompts can be included in the array for different target labels.

## Service Commands

### Basic Service Operations
```bash
# Start service with configuration
.\vista3d.exe service --config "config.json"

# Start service with custom base directory
.\vista3d.exe service --base_dir "C:\path\to\service"

# Start service with custom check interval (seconds)
.\vista3d.exe service --interval 5

# Get help
.\vista3d.exe service --help
```

### Windows Service Installation (Optional)
```bash
# Install as Windows service
.\vista3d.exe install-service

# Uninstall Windows service
.\vista3d.exe uninstall-service
```

### Direct Inference (Bypass Service)
```bash
# Run direct inference
.\vista3d.exe infer --input "path/to/scan.nii.gz" --output "path/to/output/"

# Create task file
.\vista3d.exe create-task --input "path/to/scan.nii.gz" --type "full"
```

## Performance Expectations

### Processing Times (Tested)
- **First Run**: ~4 minutes (includes model loading and initialization)
- **Subsequent Runs**: 30-60 seconds per scan
- **GPU Acceleration**: ~2.74 iterations/second during processing
- **Memory Usage**: ~6-8GB during processing

### Output
- **Segmentation File**: NIfTI format (.nii.gz)
- **Metadata**: JSON file with processing details
- **File Size**: ~300-500KB for segmentation masks
- **Labels**: Up to 118 different anatomical structures (full mode)

## Troubleshooting

### Common Issues

**"vista3d.exe not found"**
- Ensure you're in the correct directory
- Verify all files were extracted properly

**"Failed to load Python DLL"**
- The `_internal/` folder is missing or incomplete
- Re-extract the complete package

**Service not processing files**
- Check directory paths in config.json
- Ensure task files are valid JSON format
- Verify input files are in NIfTI format (.nii.gz)
- Run as Administrator

**Out of memory errors**
- Reduce concurrent tasks to 1
- Ensure sufficient RAM (16GB recommended)
- Close other applications

**Slow processing**
- Install NVIDIA GPU drivers for CUDA acceleration
- Ensure adequate cooling for sustained processing
- Use SSD storage for faster I/O

### Log Files
- **Service Log**: `vista3d_service.log`
- **CLI Log**: `vista3d_cli.log`
- Check these files for detailed error information

## Deployment Methods

### Method 1: Complete Package (Recommended)
✅ **Pros**: 
- Ready to run immediately
- No development environment needed
- All dependencies included
- Tested and verified working

❌ **Cons**: 
- Large file size (8.5GB compressed)

### Method 2: Build from Source
✅ **Pros**: 
- Smaller download (source code only)
- Can customize configuration

❌ **Cons**: 
- Requires Python development environment
- Must install PyTorch, CUDA, medical imaging libraries
- Complex build process
- Risk of dependency conflicts

**Recommendation**: Use the complete package for production deployment.

## Production Deployment Checklist

- [ ] Extract complete package to production directory
- [ ] Update config.json with correct directory paths
- [ ] Test with sample data
- [ ] Configure monitoring directories
- [ ] Set up log rotation
- [ ] Verify CUDA GPU drivers installed
- [ ] Test service startup script
- [ ] Document backup procedures
- [ ] Train end users on task file format

## Security Considerations

- Service requires Administrator privileges
- Monitor log files for sensitive information
- Implement proper file permissions on task directories
- Consider network isolation for medical data processing
- Regular updates of the service package

## Technical Details

### Supported Input Formats
- NIfTI (.nii.gz) - Primary format
- DICOM series (requires preprocessing)

### Model Information
- Architecture: VISTA3D neural network
- Labels: 118 anatomical structures (full mode)
- Input: 3D CT scans
- Output: 3D segmentation masks

### System Architecture
```
Task Directory → Service Monitor → VISTA3D Model → Output Directory
     ↓                ↓                  ↓             ↓
  JSON files    →  Processing Queue  →  GPU/CPU    →  Results
```

## Support and Updates

For technical support or updates, refer to the VISTA3D repository or contact the development team. This service has been successfully tested with real medical imaging data and is ready for production use.

---
*Last Updated: Successfully tested with complete package deployment* 