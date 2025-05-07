#!/usr/bin/env python
"""
VISTA3D Service - Automated Medical Image Segmentation
======================================================

This service monitors a folder for task files and automatically runs
VISTA3D segmentation based on the specifications in each task.

Usage:
    python vista_service.py --config config.yaml
"""

import os
import sys
import time
import json
import shutil
import logging
import argparse
import traceback
import yaml
from datetime import datetime
from pathlib import Path
import monai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vista_service.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("VISTA3D-Service")

def load_config(config_file="config.yaml"):
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        logger.info("Using default configuration")
        return {
            "service": {
                "base_directory": "./vista_service",
                "tasks_directory": "tasks",
                "processed_directory": "processed",
                "failed_directory": "failed",
                "check_interval": 30,
                "log_file": "vista_service.log"
            },
            "vista3d": {
                "config_file": "./vista3d/configs/infer.yaml",
                "device": "auto",
                "memory_efficient": True
            },
            "output": {
                "default_directory": "./output",
                "save_format": "nii.gz"
            }
        }

def setup_folders(base_dir, config=None):
    """Create necessary folder structure."""
    if config and "service" in config:
        tasks_dir = os.path.join(base_dir, config["service"]["tasks_directory"])
        processed_dir = os.path.join(base_dir, config["service"]["processed_directory"])
        failed_dir = os.path.join(base_dir, config["service"]["failed_directory"])
    else:
        tasks_dir = os.path.join(base_dir, "tasks")
        processed_dir = os.path.join(base_dir, "processed")
        failed_dir = os.path.join(base_dir, "failed")
    
    os.makedirs(tasks_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    
    return tasks_dir, processed_dir, failed_dir

def validate_task(task_data):
    """Validate task file contents."""
    required_fields = ["task_id", "input_file", "output_directory"]
    
    # Check required fields
    for field in required_fields:
        if field not in task_data:
            return False, f"Missing required field: {field}"
    
    # Check input file exists
    if not os.path.exists(task_data["input_file"]):
        return False, f"Input file does not exist: {task_data['input_file']}"
    
    # Check segmentation type
    if "segmentation_type" in task_data:
        if task_data["segmentation_type"] not in ["full", "point"]:
            return False, f"Invalid segmentation type: {task_data['segmentation_type']}"
        
        # For point-based segmentation, check required fields
        if task_data["segmentation_type"] == "point":
            if "point_coordinates" not in task_data:
                return False, "Missing point coordinates for point-based segmentation"
            if "label" not in task_data:
                return False, "Missing label for point-based segmentation"
    
    return True, "Task is valid"

def get_optimal_device(device_preference="auto"):
    """Get the optimal device for inference based on availability and preference."""
    if device_preference != "auto" and device_preference.startswith("cuda"):
        # Try to use the specified CUDA device
        try:
            import torch
            device = torch.device(device_preference)
            # Test with a small tensor
            test_tensor = torch.zeros(1, device=device)
            del test_tensor
            logger.info(f"Using specified device: {device_preference}")
            return device_preference
        except Exception as e:
            logger.warning(f"Specified device {device_preference} test failed: {str(e)}")
    
    # Auto-detect best device
    try:
        import torch
        if torch.cuda.is_available():
            # Try to use CUDA
            try:
                device = torch.device("cuda:0")
                # Test with a small tensor
                test_tensor = torch.zeros(1, device=device)
                del test_tensor
                logger.info("Using CUDA device")
                return "cuda:0"
            except Exception as e:
                logger.warning(f"CUDA device test failed: {str(e)}")
        
        # Try to use MPS (for Mac)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            try:
                device = torch.device("mps")
                test_tensor = torch.zeros(1, device=device)
                del test_tensor
                logger.info("Using MPS device")
                return "mps"
            except Exception as e:
                logger.warning(f"MPS device test failed: {str(e)}")
    except ImportError:
        logger.warning("PyTorch not available, defaulting to CPU")
    
    # Fallback to CPU
    logger.info("Using CPU device")
    return "cpu"

def run_vista3d_task(task_data, config):
    """Run VISTA3D segmentation based on task specifications."""
    from vista3d.scripts.infer import InferClass
    
    # Create output directory
    os.makedirs(task_data["output_directory"], exist_ok=True)
    
    # Get device from config
    device = get_optimal_device(config["vista3d"]["device"])
    
    # Initialize inference with device override
    infer_obj = InferClass(
        config_file=config["vista3d"]["config_file"],
        device=device
    )
    
    try:
        # Determine segmentation type
        segmentation_type = task_data.get("segmentation_type", "full")
        
        if segmentation_type == "point":
            # Point-based segmentation
            point = task_data["point_coordinates"]
            label = task_data["label"]
            
            logger.info(f"Running point-based segmentation at {point} for label {label}")
            result = infer_obj.infer(
                image_file=task_data["input_file"],
                point=[point],  # Format as [[x,y,z]]
                point_label=[label],
                save_mask=True
            )

        else:
            # Full segmentation
            from vista3d.scripts.infer import EVERYTHING_PROMPT
            logger.info(f"Running full segmentation with {len(EVERYTHING_PROMPT)} labels")
            result = infer_obj.infer(
                image_file=task_data["input_file"],
                save_mask=True,
                label_prompt=EVERYTHING_PROMPT 
            )
        
        # Save output
        if result is not None:
            import nibabel as nib
            import numpy as np
            
            output_file = os.path.join(task_data["output_directory"], "ct_seg.nii.gz")
            logger.info(f"Saving segmentation to: {output_file}")
            
            # Convert and save as NIfTI
            result_np = result.cpu().numpy().astype(np.float32)
            nifti_img = nib.Nifti1Image(result_np[0], np.eye(4))
            nib.save(nifti_img, output_file)
            
            if os.path.exists(output_file):
                logger.info(f"Segmentation saved successfully")
                file_size = os.path.getsize(output_file) / 1024
                logger.info(f"Output size: {file_size:.2f} KB")

                # If point-based segmentation was successful, create vista_roi.json
                if segmentation_type == "point":
                    vista_roi_base_dir = config["output"]["default_directory"]
                    os.makedirs(vista_roi_base_dir, exist_ok=True) # Ensure the directory exists
                    vista_roi_path = os.path.join(vista_roi_base_dir, "vista_roi.json")
                    
                    roi_info = {
                        "ROIIndex": task_data["label"], 
                        "ROIName": f"VISTA3D_Point_Label_{task_data['label']}",
                        "ROIColor": [1.0, 0.0, 0.0],  # Red color for the point-based segmentation
                        "visible": True
                    }
                    vista_roi_content = {"rois": [roi_info]}
                    with open(vista_roi_path, 'w') as f_roi:
                        json.dump(vista_roi_content, f_roi, indent=2)
                    logger.info(f"Saved VISTA ROI info for point segmentation to: {vista_roi_path}")


                
                return True, f"Segmentation completed successfully. Output: {output_file}"
        
        return False, "Inference failed to produce valid output"
    
    except Exception as e:
        logger.error(f"Error during inference: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

def process_task_file(task_file, processed_dir, failed_dir, config):
    """Process a single task file."""
    try:
        # Load task data
        with open(task_file, 'r') as f:
            task_data = json.load(f)
        
        task_id = task_data.get("task_id", os.path.basename(task_file))
        logger.info(f"Processing task: {task_id}")
        
        # Validate task
        valid, message = validate_task(task_data)
        if not valid:
            logger.error(f"Task validation failed: {message}")
            # Move to failed directory
            shutil.move(task_file, os.path.join(failed_dir, os.path.basename(task_file)))
            return False
        
        # Run VISTA3D
        success, result_message = run_vista3d_task(task_data, config)
        
        # Create result file
        result_data = {
            "task_id": task_id,
            "processed_time": datetime.now().isoformat(),
            "success": success,
            "message": result_message
        }
        
        result_file = os.path.join(
            task_data["output_directory"], 
            f"{task_id}_result.json"
        )
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        # Move task file to processed directory
        if success:
            shutil.move(task_file, os.path.join(processed_dir, os.path.basename(task_file)))
            logger.info(f"Task {task_id} completed successfully")
        else:
            shutil.move(task_file, os.path.join(failed_dir, os.path.basename(task_file)))
            logger.error(f"Task {task_id} failed: {result_message}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error processing task file {task_file}: {str(e)}")
        logger.error(traceback.format_exc())
        # Move to failed directory
        shutil.move(task_file, os.path.join(failed_dir, os.path.basename(task_file)))
        return False

def monitor_tasks_folder(tasks_dir, processed_dir, failed_dir, interval=5, config=None):
    """Monitor tasks folder for new task files."""
    logger.info(f"Starting VISTA3D service. Monitoring {tasks_dir} every {interval} seconds")
    
    while True:
        try:
            # Get all JSON files in tasks directory
            task_files = [os.path.join(tasks_dir, f) for f in os.listdir(tasks_dir) if f.endswith('.json')]
            
            if task_files:
                logger.info(f"Found {len(task_files)} task files")
                
                # Process each task file
                for task_file in task_files:
                    process_task_file(task_file, processed_dir, failed_dir, config)
            
            # Wait for next check
            time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
        
        except Exception as e:
            logger.error(f"Error in monitoring loop: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(interval)  # Continue monitoring even after error

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="VISTA3D Service")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--base_dir", help="Base directory for service files (overrides config)")
    parser.add_argument("--interval", type=int, help="Interval in seconds to check for new tasks (overrides config)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments if provided
    base_dir = args.base_dir or config["service"]["base_directory"]
    interval = args.interval or config["service"]["check_interval"]
    
    # Setup folders
    tasks_dir, processed_dir, failed_dir = setup_folders(base_dir, config)
    
    # Start monitoring
    monitor_tasks_folder(tasks_dir, processed_dir, failed_dir, interval, config)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
