#!/usr/bin/env python
"""
VISTA3D Command Line Interface
=============================

A unified command-line interface for VISTA3D that supports both:
1. Direct inference mode - for quick segmentation of a single CT scan
2. Service mode - for continuous processing of multiple tasks

Usage:
    # Direct inference mode
    vista3d_cli.py infer --input "path/to/ct.nii.gz" --output "path/to/output" --type full
    vista3d_cli.py infer --input "path/to/ct.nii.gz" --output "path/to/output" --type point --point "175,136,141" --label 1
    
    # Service mode
    vista3d_cli.py service --config "config.yaml"
    
    # Create a task for service mode
    vista3d_cli.py create-task --input "path/to/ct.nii.gz" --output "path/to/output" --type full
    
    # Install as a Windows service
    vista3d_cli.py install-service
    
    # Uninstall the Windows service
    vista3d_cli.py uninstall-service
"""

import os
import sys
import argparse
import logging
import subprocess
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vista3d_cli.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("VISTA3D-CLI")

def setup_environment():
    """Ensure the environment is properly set up."""
    # Create necessary directories if they don't exist
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vista_service")
    os.makedirs(os.path.join(base_dir, "tasks"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "processed"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "failed"), exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    logger.info("Environment setup complete")

def run_inference(args):
    """Run direct inference on a CT scan."""
    from vista_service import run_vista3d_task
    import yaml
    
    # Load config
    config_file = args.config or "config.yaml"
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
    from create_task import create_task_file
    
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
    task_args.tasks_dir = args.tasks_dir
    
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
    from vista_service import main as service_main
    
    # Override sys.argv for the service
    sys.argv = ["vista_service.py"]
    if args.config:
        sys.argv.extend(["--config", args.config])
    if args.base_dir:
        sys.argv.extend(["--base_dir", args.base_dir])
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
        
        # Get the current script path
        script_path = os.path.abspath(sys.argv[0])
        
        # Create a batch file for the service
        service_bat = os.path.join(os.path.dirname(script_path), "vista3d_service.bat")
        with open(service_bat, 'w') as f:
            f.write('@echo off\n')
            f.write('echo Starting VISTA3D Service...\n')
            f.write(f'"{sys.executable}" "{script_path}" service\n')
        
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

def main():
    """Main entry point for the CLI."""
    # Create the top-level parser
    parser = argparse.ArgumentParser(description="VISTA3D Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
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
    task_parser.add_argument("--tasks_dir", default="./vista_service/tasks", help="Directory to save task files")
    
    # Parser for the "service" command
    service_parser = subparsers.add_parser("service", help="Run the VISTA3D service")
    service_parser.add_argument("--config", help="Path to configuration file")
    service_parser.add_argument("--base_dir", help="Base directory for service files")
    service_parser.add_argument("--interval", type=int, help="Interval in seconds to check for new tasks")
    
    # Parser for the "install-service" command
    subparsers.add_parser("install-service", help="Install VISTA3D as a Windows service")
    
    # Parser for the "uninstall-service" command
    subparsers.add_parser("uninstall-service", help="Uninstall the VISTA3D Windows service")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup environment
    setup_environment()
    
    # Run the appropriate command
    if args.command == "infer":
        return run_inference(args)
    elif args.command == "create-task":
        return create_task(args)
    elif args.command == "service":
        return run_service(args)
    elif args.command == "install-service":
        return install_service()
    elif args.command == "uninstall-service":
        return uninstall_service()
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
