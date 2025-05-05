#!/usr/bin/env python
"""
Create a single-file installer for VISTA3D
"""
import os
import sys
import subprocess

# Create the spec file content
spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['vista3d_cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('vista3d', 'vista3d'),
        ('config.yaml', '.'),
        ('README.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'torch',
        'monai',
        'nibabel',
        'yaml',
        'numpy',
        'vista3d.scripts.infer',
        'vista3d.modeling',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='vista3d_installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

# Write the spec file
with open('vista3d_installer.spec', 'w') as f:
    f.write(spec_content)

print("Created vista3d_installer.spec")

# Create the installer CLI script
installer_cli_content = """#!/usr/bin/env python
\"\"\"
VISTA3D Installer and CLI
=========================

A unified installer and command-line interface for VISTA3D that:
1. Installs necessary components on first run
2. Supports both direct inference and service modes
3. Can be installed as a Windows service

Usage:
    # First-time setup
    vista3d_installer.exe setup

    # Direct inference mode
    vista3d_installer.exe infer --input "path/to/ct.nii.gz" --output "path/to/output" --type full
    vista3d_installer.exe infer --input "path/to/ct.nii.gz" --output "path/to/output" --type point --point "175,136,141" --label 1
    
    # Service mode
    vista3d_installer.exe service --config "config.yaml"
    
    # Create a task for service mode
    vista3d_installer.exe create-task --input "path/to/ct.nii.gz" --output "path/to/output" --type full
    
    # Install as a Windows service
    vista3d_installer.exe install-service
    
    # Uninstall the Windows service
    vista3d_installer.exe uninstall-service
\"\"\"

import os
import sys
import argparse
import logging
import subprocess
import json
import shutil
from pathlib import Path
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vista3d_installer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("VISTA3D-Installer")

# Determine if we're running from the installer or extracted files
def is_running_from_installer():
    """Check if we're running from the installer or extracted files."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Get the base directory for VISTA3D files
def get_vista3d_dir():
    """Get the base directory for VISTA3D files."""
    if is_running_from_installer():
        # When running from the installer, use the user's AppData directory
        vista3d_dir = os.path.join(os.environ['APPDATA'], 'VISTA3D')
    else:
        # When running from source, use the current directory
        vista3d_dir = os.path.dirname(os.path.abspath(__file__))
    
    return vista3d_dir

def setup_environment():
    """Set up the VISTA3D environment."""
    vista3d_dir = get_vista3d_dir()
    
    # Create the VISTA3D directory if it doesn't exist
    os.makedirs(vista3d_dir, exist_ok=True)
    
    # Create necessary subdirectories
    os.makedirs(os.path.join(vista3d_dir, "vista_service", "tasks"), exist_ok=True)
    os.makedirs(os.path.join(vista3d_dir, "vista_service", "processed"), exist_ok=True)
    os.makedirs(os.path.join(vista3d_dir, "vista_service", "failed"), exist_ok=True)
    os.makedirs(os.path.join(vista3d_dir, "output"), exist_ok=True)
    
    # If running from the installer, extract necessary files
    if is_running_from_installer():
        # Copy files from the temporary directory to the VISTA3D directory
        temp_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        
        # Copy the vista3d directory
        if os.path.exists(os.path.join(temp_dir, "vista3d")):
            if os.path.exists(os.path.join(vista3d_dir, "vista3d")):
                shutil.rmtree(os.path.join(vista3d_dir, "vista3d"))
            shutil.copytree(os.path.join(temp_dir, "vista3d"), os.path.join(vista3d_dir, "vista3d"))
        
        # Copy config files
        for file in ["config.yaml", "README.md", "requirements.txt"]:
            if os.path.exists(os.path.join(temp_dir, file)):
                shutil.copy2(os.path.join(temp_dir, file), os.path.join(vista3d_dir, file))
        
        # Create a batch file to run the installer from the VISTA3D directory
        batch_file = os.path.join(vista3d_dir, "vista3d.bat")
        with open(batch_file, 'w') as f:
            f.write('@echo off\n')
            f.write(f'"{sys.executable}" "%~dp0\\vista3d_installer.py" %*\n')
        
        # Create a copy of the installer in the VISTA3D directory
        shutil.copy2(sys.executable, os.path.join(vista3d_dir, "vista3d_installer.exe"))
        
        # Create a copy of the installer script in the VISTA3D directory
        if os.path.exists(__file__):
            shutil.copy2(__file__, os.path.join(vista3d_dir, "vista3d_installer.py"))
    
    logger.info(f"Environment set up in {vista3d_dir}")
    return vista3d_dir

def run_inference(args):
    """Run direct inference on a CT scan."""
    vista3d_dir = get_vista3d_dir()
    
    # Add the VISTA3D directory to the Python path
    sys.path.insert(0, vista3d_dir)
    
    # Import the necessary modules
    try:
        from vista_service import run_vista3d_task
        import yaml
    except ImportError:
        logger.error("Failed to import required modules. Make sure VISTA3D is properly installed.")
        return 1
    
    # Load config
    config_file = args.config or os.path.join(vista3d_dir, "config.yaml")
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        config = {
            "vista3d": {
                "config_file": "./vista3d/configs/infer.yaml",
                "device": "auto"
            }
        }
    
    # Create task data
    task_data = {
        "task_id": "direct_inference",
        "input_file": args.input,
        "output_directory": args.output,
        "segmentation_type": args.type
    }
    
    # Add point data if needed
    if args.type == "point":
        if not args.point:
            logger.error("Point coordinates must be provided for point-based segmentation")
            return 1
        if not args.label:
            logger.error("Label must be provided for point-based segmentation")
            return 1
        
        # Parse point coordinates
        point_coords = [float(x) for x in args.point.split(",")]
        if len(point_coords) != 3:
            logger.error("Point coordinates must be in format 'x,y,z'")
            return 1
        
        task_data["point_coordinates"] = point_coords
        task_data["label"] = args.label
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Run inference
    logger.info(f"Running {args.type} segmentation on {args.input}")
    success, message = run_vista3d_task(task_data, config)
    
    if success:
        logger.info(f"Segmentation completed successfully: {message}")
        return 0
    else:
        logger.error(f"Segmentation failed: {message}")
        return 1

def create_task(args):
    """Create a task file for the service."""
    vista3d_dir = get_vista3d_dir()
    
    # Add the VISTA3D directory to the Python path
    sys.path.insert(0, vista3d_dir)
    
    # Import the necessary modules
    try:
        from create_task import create_task_file
    except ImportError:
        logger.error("Failed to import required modules. Make sure VISTA3D is properly installed.")
        return 1
    
    # Create args object with the right structure for create_task_file
    class TaskArgs:
        pass
    
    task_args = TaskArgs()
    task_args.task_id = args.task_id
    task_args.input = args.input
    task_args.output = args.output
    task_args.type = args.type
    task_args.point = args.point
    task_args.label = args.label
    task_args.description = args.description
    task_args.tasks_dir = args.tasks_dir or os.path.join(vista3d_dir, "vista_service", "tasks")
    
    # Create task file
    try:
        task_file = create_task_file(task_args)
        logger.info(f"Task file created: {task_file}")
        return 0
    except Exception as e:
        logger.error(f"Error creating task file: {str(e)}")
        return 1

def run_service(args):
    """Run the VISTA3D service."""
    vista3d_dir = get_vista3d_dir()
    
    # Add the VISTA3D directory to the Python path
    sys.path.insert(0, vista3d_dir)
    
    # Import the necessary modules
    try:
        from vista_service import main as service_main
    except ImportError:
        logger.error("Failed to import required modules. Make sure VISTA3D is properly installed.")
        return 1
    
    # Override sys.argv for the service
    sys.argv = ["vista_service.py"]
    if args.config:
        sys.argv.extend(["--config", args.config])
    if args.base_dir:
        sys.argv.extend(["--base_dir", args.base_dir])
    else:
        sys.argv.extend(["--base_dir", os.path.join(vista3d_dir, "vista_service")])
    if args.interval:
        sys.argv.extend(["--interval", str(args.interval)])
    
    # Run the service
    return service_main()

def install_service():
    """Install VISTA3D as a Windows service."""
    try:
        # Check if we're on Windows
        if os.name != 'nt':
            logger.error("Service installation is only supported on Windows")
            return 1
        
        vista3d_dir = get_vista3d_dir()
        
        # Get the installer path
        installer_path = os.path.join(vista3d_dir, "vista3d_installer.exe")
        if not os.path.exists(installer_path):
            installer_path = sys.executable
        
        # Create a batch file for the service
        service_bat = os.path.join(vista3d_dir, "vista3d_service.bat")
        with open(service_bat, 'w') as f:
            f.write('@echo off\n')
            f.write('echo Starting VISTA3D Service...\n')
            f.write(f'"{installer_path}" service\n')
        
        # Create a scheduled task
        task_name = "VISTA3D_Service"
        cmd = [
            "schtasks", "/create", "/tn", task_name, 
            "/tr", f'"{service_bat}"', 
            "/sc", "onstart", 
            "/ru", "SYSTEM",
            "/f"  # Force creation if it already exists
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("VISTA3D service installed successfully")
            logger.info("The service will start automatically when the system boots")
            logger.info(f"To start it manually, run: schtasks /run /tn {task_name}")
            return 0
        else:
            logger.error(f"Failed to install service: {result.stderr}")
            return 1
            
    except Exception as e:
        logger.error(f"Error installing service: {str(e)}")
        return 1

def uninstall_service():
    """Uninstall the VISTA3D Windows service."""
    try:
        # Check if we're on Windows
        if os.name != 'nt':
            logger.error("Service uninstallation is only supported on Windows")
            return 1
        
        # Delete the scheduled task
        task_name = "VISTA3D_Service"
        cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("VISTA3D service uninstalled successfully")
            return 0
        else:
            logger.error(f"Failed to uninstall service: {result.stderr}")
            return 1
            
    except Exception as e:
        logger.error(f"Error uninstalling service: {str(e)}")
        return 1

def batch_process(args):
    """Process multiple CT scans in batch mode."""
    vista3d_dir = get_vista3d_dir()
    
    # Add the VISTA3D directory to the Python path
    sys.path.insert(0, vista3d_dir)
    
    # Import the necessary modules
    try:
        from batch_process_totalsegmentator import main as batch_main
    except ImportError:
        logger.error("Failed to import required modules. Make sure VISTA3D is properly installed.")
        return 1
    
    # Override sys.argv for the batch process
    sys.argv = ["batch_process_totalsegmentator.py"]
    if args.count:
        sys.argv.extend(["--count", str(args.count)])
    if args.type:
        sys.argv.extend(["--type", args.type])
    if args.wait:
        sys.argv.extend(["--wait", str(args.wait)])
    
    # Run the batch process
    return batch_main()

def main():
    """Main entry point for the installer and CLI."""
    # Create the top-level parser
    parser = argparse.ArgumentParser(description="VISTA3D Installer and CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Parser for the "setup" command
    setup_parser = subparsers.add_parser("setup", help="Set up the VISTA3D environment")
    
    # Parser for the "infer" command
    infer_parser = subparsers.add_parser("infer", help="Run direct inference on a CT scan")
    infer_parser.add_argument("--input", required=True, help="Input CT scan file")
    infer_parser.add_argument("--output", required=True, help="Output directory for segmentation results")
    infer_parser.add_argument("--type", choices=["full", "point"], default="full", help="Segmentation type")
    infer_parser.add_argument("--point", help="Point coordinates (x,y,z) for point-based segmentation")
    infer_parser.add_argument("--label", type=int, help="Label for point-based segmentation")
    infer_parser.add_argument("--config", help="Path to configuration file")
    
    # Parser for the "create-task" command
    task_parser = subparsers.add_parser("create-task", help="Create a task file for the service")
    task_parser.add_argument("--task_id", help="Unique task identifier (generated if not provided)")
    task_parser.add_argument("--input", required=True, help="Input CT scan file")
    task_parser.add_argument("--output", required=True, help="Output directory for segmentation results")
    task_parser.add_argument("--type", choices=["full", "point"], default="full", help="Segmentation type")
    task_parser.add_argument("--point", help="Point coordinates (x,y,z) for point-based segmentation")
    task_parser.add_argument("--label", type=int, help="Label for point-based segmentation")
    task_parser.add_argument("--description", help="Task description")
    task_parser.add_argument("--tasks_dir", help="Directory to save task files")
    
    # Parser for the "service" command
    service_parser = subparsers.add_parser("service", help="Run the VISTA3D service")
    service_parser.add_argument("--config", help="Path to configuration file")
    service_parser.add_argument("--base_dir", help="Base directory for service files")
    service_parser.add_argument("--interval", type=int, help="Interval in seconds to check for new tasks")
    
    # Parser for the "batch-process" command
    batch_parser = subparsers.add_parser("batch-process", help="Process multiple CT scans in batch mode")
    batch_parser.add_argument("--count", type=int, default=10, help="Number of CT scans to process")
    batch_parser.add_argument("--type", choices=["full", "point"], default="full", help="Segmentation type")
    batch_parser.add_argument("--wait", type=int, default=5, help="Wait time between task creation in seconds")
    
    # Parser for the "install-service" command
    subparsers.add_parser("install-service", help="Install VISTA3D as a Windows service")
    
    # Parser for the "uninstall-service" command
    subparsers.add_parser("uninstall-service", help="Uninstall the VISTA3D Windows service")
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return 0
    
    # Set up the environment
    if args.command == "setup":
        vista3d_dir = setup_environment()
        print(f"VISTA3D environment set up in {vista3d_dir}")
        print("You can now use VISTA3D with the following commands:")
        print("  vista3d_installer.exe infer --input <file> --output <dir> --type full")
        print("  vista3d_installer.exe service")
        print("  vista3d_installer.exe install-service")
        return 0
    
    # For all other commands, make sure the environment is set up
    vista3d_dir = get_vista3d_dir()
    if not os.path.exists(vista3d_dir):
        setup_environment()
    
    # Run the appropriate command
    if args.command == "infer":
        return run_inference(args)
    elif args.command == "create-task":
        return create_task(args)
    elif args.command == "service":
        return run_service(args)
    elif args.command == "batch-process":
        return batch_process(args)
    elif args.command == "install-service":
        return install_service()
    elif args.command == "uninstall-service":
        return uninstall_service()
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
"""

# Write the installer CLI script
with open('vista3d_installer.py', 'w') as f:
    f.write(installer_cli_content)

print("Created vista3d_installer.py")

# Create a batch file to build the installer
build_script = """@echo off
echo Building VISTA3D Installer
echo ========================
echo.

pyinstaller vista3d_installer.spec

echo.
echo Build complete!
echo The installer is available at: dist\\vista3d_installer.exe
echo.
pause
"""

with open('build_installer.bat', 'w') as f:
    f.write(build_script)

print("Created build_installer.bat")

print("Setup complete!")
print("To build the installer, run build_installer.bat")
