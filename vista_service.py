# vista_service.py
#!/usr/bin/env python
"""
VISTA3D Service - Automated Medical Image Segmentation
======================================================

This service monitors a folder for task files and automatically runs
VISTA3D segmentation based on the specifications in each task.

Usage:
    python vista_service.py --config config.json
"""

import os
import sys
import time
import json
import shutil
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path
import monai

try:
    import torch
    import numpy as np
    import nibabel as nib
except ImportError as e:
    logging.warning(f"PyTorch, NumPy, or Nibabel not found. Some features might be limited: {e}")
    torch = None
    np = None
    nib = None


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

def normalize_path(path, base_dir=None):
    if path is None:
        return None
    path = path.replace('\\', '/')
    if not os.path.isabs(path) and base_dir:
        path = os.path.join(base_dir, path)
    return os.path.normpath(os.path.abspath(path))

def load_config(config_file="config.json"):
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        logger.info(f"config: {config}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        logger.info("Using default configuration")
        return {
            "service": {
                "base_directory": "./vista_service",
                "tasks_directory": "Tasks",
                "taskshistory_directory": "TasksHistory",
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
        tasks_dir = normalize_path(os.path.join(base_dir, config["service"]["tasks_directory"]))
        taskshistory_dir = normalize_path(os.path.join(base_dir, config["service"]["taskshistory_directory"]))
    else:
        tasks_dir = os.path.join(base_dir, "tasks")
        taskshistory_dir = os.path.join(base_dir, "taskshistory")
    
    os.makedirs(tasks_dir, exist_ok=True)
    os.makedirs(taskshistory_dir, exist_ok=True)
    
    return tasks_dir, taskshistory_dir

def validate_task(task_data):
    """Validate task file contents."""
    required_fields = ["task_id", "input_file", "output_directory"]
    
    for field in required_fields:
        if field not in task_data:
            return False, f"Missing required field: {field}"
    
    if not os.path.exists(task_data["input_file"]):
        return False, f"Input file does not exist: {task_data['input_file']}"
    
    segmentation_type = task_data.get("segmentation_type", "full") # Default to full
    task_data["segmentation_type"] = segmentation_type # Ensure it's in task_data for later use

    if segmentation_type not in ["full", "point"]:
        return False, f"Invalid segmentation type: {segmentation_type}"
        
    if segmentation_type == "point":
        if not all([torch, np, nib]):
            return False, "PyTorch, NumPy, or Nibabel is not installed. 'point' segmentation is unavailable."
        if "segmentation_prompts" not in task_data:
            return False, "Missing 'segmentation_prompts' for point segmentation"
        if not isinstance(task_data["segmentation_prompts"], list) or not task_data["segmentation_prompts"]:
            return False, "'segmentation_prompts' must be a non-empty list"

        for i, prompt_spec in enumerate(task_data["segmentation_prompts"]):
            if not isinstance(prompt_spec, dict):
                return False, f"Prompt spec at index {i} must be a dictionary"
            if "target_output_label" not in prompt_spec or not isinstance(prompt_spec["target_output_label"], int):
                return False, f"Missing or invalid 'target_output_label' (must be int) in prompt spec at index {i}"
            
            positive_points = prompt_spec.get("positive_points", [])
            negative_points = prompt_spec.get("negative_points", [])

            if not isinstance(positive_points, list) or not isinstance(negative_points, list):
                return False, f"positive_points/negative_points must be lists in prompt spec at index {i}"
            
            if not positive_points and not negative_points:
                 return False, f"At least one positive or negative point must be provided for prompt spec at index {i} (target_label: {prompt_spec['target_output_label']})"

            for p_type_name, points_list in [("positive_points", positive_points), ("negative_points", negative_points)]:
                for p_coord in points_list:
                    if not isinstance(p_coord, list) or len(p_coord) != 3:
                        return False, f"Each point in '{p_type_name}' must be a list of 3 numbers (x,y,z) in prompt spec at index {i}"
                    if not all(isinstance(c, (int, float)) for c in p_coord):
                        return False, f"Point coordinates must be numbers in '{p_type_name}' in prompt spec at index {i}"
    
    return True, "Task is valid"

def get_optimal_device(device_preference="auto"):
    """Get the optimal device for inference based on availability and preference."""
    # Auto-detect best device
    try:
        if torch is None: # PyTorch not available
            logger.warning("PyTorch not available, defaulting to CPU for device selection logic.")
            return "cpu"

        if device_preference != "auto" and device_preference.startswith("cuda"):
            try:
                device = torch.device(device_preference)
                test_tensor = torch.zeros(1, device=device) # Test specified CUDA device
                del test_tensor
                logger.info(f"Using specified device: {device_preference}")
                return device_preference
            except Exception as e:
                logger.warning(f"Specified device {device_preference} test failed: {str(e)}. Falling back to auto-detection.")
        
        if torch.cuda.is_available():
            try:
                device = torch.device("cuda:0")
                test_tensor = torch.zeros(1, device=device)
                del test_tensor
                logger.info("Using CUDA device (cuda:0)")
                return "cuda:0"
            except Exception as e:
                logger.warning(f"CUDA device test failed: {str(e)}")
        
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            try:
                device = torch.device("mps")
                test_tensor = torch.zeros(1, device=device)
                del test_tensor
                logger.info("Using MPS device")
                return "mps"
            except Exception as e:
                logger.warning(f"MPS device test failed: {str(e)}")
    except ImportError: # This case should be caught by torch is None check earlier
        logger.warning("PyTorch not available, defaulting to CPU")
    
    logger.info("Using CPU device")
    return "cpu"

def run_vista3d_task(task_data, config):
    """Run VISTA3D segmentation based on task specifications."""
    from vista3d.scripts.infer import InferClass, EVERYTHING_PROMPT
    
    os.makedirs(task_data["output_directory"], exist_ok=True)
    device = get_optimal_device(config["vista3d"]["device"])
    
    logger.info(f"Using config file for inference: {config["vista3d"]["config_file"]}")

    infer_obj = InferClass(
        config_file=config["vista3d"]["config_file"],
        device=device # Pass the determined device to InferClass
    )
    
    try:
        segmentation_type = task_data["segmentation_type"] # Already validated and set

        if segmentation_type == "point":
            if not all([torch, np, nib]): # Should have been caught by validation
                 return False, "Cannot run 'point': PyTorch, NumPy or Nibabel missing."

            logger.info("Running point-based segmentation for multiple target labels.")
            all_individual_segmentations = []
            processed_target_labels = []
            first_processed_mask_metadata = None

            # Clear infer_obj cache if it exists and is used for image data across calls
            # if hasattr(infer_obj, 'clear_cache') and callable(infer_obj.clear_cache):
            #     infer_obj.clear_cache()
            #     logger.info("Cleared infer_obj cache for point segmentation.")

            # initial_image_data_for_transform = task_data["input_file"]

            for i, prompt_spec in enumerate(task_data.get("segmentation_prompts", [])):
                target_label = prompt_spec["target_output_label"]
                positive_points = prompt_spec.get("positive_points", [])
                negative_points = prompt_spec.get("negative_points", [])
                display_name = prompt_spec.get("display_name", f"Label {target_label}")
                print("\n\nprompt_spec:", prompt_spec)
                print("\ntask_data: ", task_data)
                
                current_points = positive_points + negative_points
                if not current_points:
                    logger.warning(f"No points for target_label {target_label}. Skipping.")
                    continue

                current_point_types = [1] * len(positive_points) + [0] * len(negative_points)

                logger.info(f"Processing target_label: {target_label} with {len(positive_points)} pos, {len(negative_points)} neg points.")
                
                # If infer_obj.batch_data is cached, clear for subsequent calls if needed
                # The check/call above should handle this for the whole loop.
                # If more granular control is needed per-prompt, add infer_obj.clear_cache() here.
                if hasattr(infer_obj, 'clear_cache') and callable(infer_obj.clear_cache):
                    infer_obj.clear_cache()
                    logger.info(f"InferClass cache cleared for target_label: {target_label}")

                result_tensor = infer_obj.infer(
                    image_file=task_data["input_file"],
                    point=current_points,
                    point_label=current_point_types,
                    prompt_class=[target_label], 
                    save_mask=False # Aggregate and save once
                )
                
                if result_tensor is not None:
                    all_individual_segmentations.append({
                        "label_id": target_label,
                        "mask_tensor": result_tensor.cpu(),
                        "display_name": display_name
                    })
                    processed_target_labels.append(target_label)
                    if first_processed_mask_metadata is None:
                        if hasattr(result_tensor, 'affine') and hasattr(result_tensor, 'shape'):
                             first_processed_mask_metadata = {
                                'affine': result_tensor.affine.cpu().numpy() if hasattr(result_tensor.affine, 'cpu') else result_tensor.affine,
                                'shape': result_tensor.shape
                            }
                        else:
                            logger.warning("Could not get metadata directly from first result tensor.")
                else:
                    logger.warning(f"Inference failed for target_label: {target_label}")

            if not all_individual_segmentations or first_processed_mask_metadata is None:
                return False, "Point segmentation failed: no results or metadata unavailable."

            final_mask_shape = first_processed_mask_metadata['shape']
            if len(final_mask_shape) == 4 and final_mask_shape[0] == 1: # Expected [1, H, W, D]
                final_mask_shape = final_mask_shape[1:]
            
            final_combined_mask = torch.zeros(final_mask_shape, dtype=torch.int16)

            for seg_info in all_individual_segmentations:
                label_id = seg_info["label_id"]
                mask_tensor = seg_info["mask_tensor"] # Expected [1,H,W,D] from infer
                
                # Binarize: assume positive values in mask_tensor mean presence of the class
                # Squeeze to remove channel dim: [H,W,D]
                binary_class_mask = (mask_tensor.squeeze(0) > 0.5).long() 
                final_combined_mask[binary_class_mask == 1] = label_id
            
            output_file = os.path.join(task_data["output_directory"], "ct_seg.nii.gz")
            nifti_img = nib.Nifti1Image(final_combined_mask.numpy().astype(np.int16), 
                                        first_processed_mask_metadata['affine'])
            nib.save(nifti_img, output_file)
            logger.info(f"Saved combined multi-label segmentation to: {output_file}")

            # Generate ct_seg.json
            vista_roi_path = os.path.join(task_data["output_directory"], "ct_seg.json")
            unique_labels_for_roi = sorted(list(set(processed_target_labels)))
            rois_list = []
            roi_colors = [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.5, 0.5, 1.0],
                [0.0, 0.5, 1.0],
                [1.0, 0.5, 1.0],
                [1.0, 0.5, 0.0],
                [0.2, 0.5, 0.2],
                [0.2, 0.8, 0.4],
                [1.0, 0.0, 0.5],
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [1.0, 0.0, 0.5],
                [0.0, 0.5, 0.5],
                [0.5, 0.0, 1.0],
                [1.0, 0.2, 0.2],
                [0.7, 0.7, 0.0],
                [0.2, 0.2, 0.7],
                [0.0, 0.7, 0.7],
                [0.7, 0.0, 0.7],
                [0.7, 0.5, 0.2],
                [0.4, 0.7, 0.2],
                [0.8, 0.2, 0.8],
                [0.8, 0.8, 0.2],
                [0.2, 0.8, 0.8],
                [0.8, 0.2, 0.2],
                [0.5, 0.2, 0.7],
                [0.7, 0.5, 0.7],
                [0.5, 0.7, 0.2],
                [0.2, 0.7, 0.5],
                [0.7, 0.2, 0.5],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.5, 0.5, 1.0],
                [0.0, 0.5, 1.0],
                [1.0, 0.5, 1.0],
                [1.0, 0.5, 0.0],
                [0.2, 0.5, 0.2],
                [0.2, 0.8, 0.4],
                [1.0, 0.0, 0.5],
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [1.0, 0.0, 0.5],
                [0.0, 0.5, 0.5],
                [0.5, 0.0, 1.0],
                [1.0, 0.2, 0.2],
                [0.7, 0.7, 0.0],
                [0.2, 0.2, 0.7],
                [0.0, 0.7, 0.7],
                [0.7, 0.0, 0.7],
                [0.7, 0.5, 0.2],
                [0.4, 0.7, 0.2],
                [0.8, 0.2, 0.8],
                [0.8, 0.8, 0.2],
                [0.2, 0.8, 0.8],
                [0.8, 0.2, 0.2],
                [0.5, 0.2, 0.7],
                [0.7, 0.5, 0.7],
                [0.5, 0.7, 0.2],
                [0.2, 0.7, 0.5],
                [0.7, 0.2, 0.5],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.5, 0.5, 1.0],
                [0.0, 0.5, 1.0],
                [1.0, 0.5, 1.0],
                [1.0, 0.5, 0.0],
                [0.2, 0.5, 0.2],
                [0.2, 0.8, 0.4],
                [1.0, 0.0, 0.5],
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [1.0, 0.0, 0.5],
                [0.0, 0.5, 0.5],
                [0.5, 0.0, 1.0],
                [1.0, 0.2, 0.2],
                [0.7, 0.7, 0.0],
                [0.2, 0.2, 0.7],
                [0.0, 0.7, 0.7],
                [0.7, 0.0, 0.7],
                [0.7, 0.5, 0.2],
                [0.4, 0.7, 0.2],
                [0.8, 0.2, 0.8],
                [0.8, 0.8, 0.2],
                [0.2, 0.8, 0.8],
                [0.8, 0.2, 0.2],
                [0.5, 0.2, 0.7],
                [0.7, 0.5, 0.7],
                [0.5, 0.7, 0.2],
                [0.2, 0.7, 0.5],
                [0.7, 0.2, 0.5],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.5, 0.5, 1.0],
                [0.0, 0.5, 1.0],
                [1.0, 0.5, 1.0],
                [1.0, 0.5, 0.0],
                [0.2, 0.5, 0.2],
                [0.2, 0.8, 0.4],
                [1.0, 0.0, 0.5],
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [1.0, 0.0, 0.5],
                [0.0, 0.5, 0.5],
                [0.5, 0.0, 1.0],
                [1.0, 0.2, 0.2],
                [0.7, 0.7, 0.0],
                [0.2, 0.2, 0.7],
                [0.0, 0.7, 0.7],
                [0.7, 0.0, 0.7],
                [0.7, 0.5, 0.2],
                [0.4, 0.7, 0.2],
                [0.8, 0.2, 0.8],
                [0.8, 0.8, 0.2],
                [0.2, 0.8, 0.8],
                [0.8, 0.2, 0.2],
                [0.5, 0.2, 0.7],
                [0.7, 0.5, 0.7],
                [0.5, 0.7, 0.2],
                [0.2, 0.7, 0.5],
                [0.7, 0.2, 0.5]
            ]
            for seg_info in all_individual_segmentations:
                if seg_info["label_id"] not in unique_labels_for_roi:
                    continue

                current_prompt_spec = None
                for prompt_spec_item in task_data.get("segmentation_prompts", []):
                    if prompt_spec_item["target_output_label"] == seg_info["label_id"]:
                        current_prompt_spec = prompt_spec_item
                        break


                roi_center_physical = None

                if current_prompt_spec:
                    physical_center_from_rust = current_prompt_spec.get("physical_center_of_box")
                    if physical_center_from_rust and isinstance(physical_center_from_rust, list) and len(physical_center_from_rust) == 3:
                        roi_center_physical = physical_center_from_rust
                    else:
                        points_for_center_voxel = []
                        positive_points_voxel = current_prompt_spec.get("positive_points", [])
                        if positive_points_voxel:
                            points_for_center_voxel = positive_points_voxel
                        elif not points_for_center_voxel:
                            negative_points_voxel = current_prompt_spec.get("negative_points", [])
                            if negative_points_voxel:
                                points_for_center_voxel = negative_points_voxel
                        
                        if points_for_center_voxel:
                            # Use the first point from the chosen list
                            first_voxel_point = np.array(points_for_center_voxel[0] + [1]) # Homogeneous voxel coords
                            try:
                                if nib and np: # Ensure nibabel and numpy are available
                                    img_affine = nib.load(task_data["input_file"]).affine
                                    physical_coords = img_affine @ first_voxel_point
                                    roi_center_physical = physical_coords[:3].tolist()
                                else:
                                    logger.warning("nibabel or numpy not available for physical coordinate conversion. ROICenter will be voxel.")
                                    roi_center_physical = points_for_center_voxel[0] # Fallback to voxel
                            except Exception as e:
                                logger.warning(f"Could not convert voxel center to physical for ROI {seg_info['label_id']}: {e}")
                                roi_center_physical = points_for_center_voxel[0] # Fallback to voxel if conversion fails





                color_idx = unique_labels_for_roi.index(seg_info["label_id"])
                rois_list.append({
                    "ROIIndex": seg_info["label_id"], "ROIName": seg_info["display_name"],
                    "ROIColor": roi_colors[color_idx % len(roi_colors)], "visible": True, 
                    "ROICenter": roi_center_physical
                })
            with open(vista_roi_path, 'w') as f_roi:
                json.dump({"rois": rois_list}, f_roi, indent=2)
            logger.info(f"Saved VISTA ROI info to: {vista_roi_path}")
            return True, "Point segmentation completed successfully."

        else: # Full segmentation
            logger.info(f"Running full segmentation with {len(EVERYTHING_PROMPT)} labels")
            result = infer_obj.infer(
                image_file=task_data["input_file"],
                save_mask=True, # As per original logic
                label_prompt=EVERYTHING_PROMPT 
            )
            # Similar to "point" mode, if `save_mask=True` is used, `infer` returns the tensor.
            if result is not None:
                output_file = os.path.join(task_data["output_directory"], "ct_seg.nii.gz")
                logger.info(f"Saving full segmentation to: {output_file}")
                
                result_np = result.cpu().numpy().astype(np.float32) # Or np.int16
                nifti_img = nib.Nifti1Image(result_np[0], result.affine.cpu().numpy() if hasattr(result, 'affine') else np.eye(4))
                nib.save(nifti_img, output_file)
                
                if os.path.exists(output_file):
                    logger.info(f"Full segmentation saved successfully")
                    # No vista_roi.json for full segmentation by default in this service
                    return True, "Full segmentation completed successfully."
                else:
                    return False, "Failed to save full segmentation."
            else:
                return False, "Full inference failed to produce valid output."
    
    except Exception as e:
        logger.error(f"Error during VISTA3D task execution: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

def process_task_file(task_file, taskshistory_dir, config):
    """Process a single task file."""
    try:
        with open(task_file, 'r') as f:
            task_data = json.load(f)
        
        task_id = task_data.get("task_id", os.path.basename(task_file))
        logger.info(f"Processing Task ID: {task_id}, File: {task_file}")
        # logger.info(f"Task Data: {json.dumps(task_data, indent=2)}") # More readable log
        
        valid, message = validate_task(task_data)
        if not valid:
            logger.error(f"Task validation failed for {task_id}: {message}")
            destination = os.path.join(taskshistory_dir, f"failed_validation_{os.path.basename(task_file)}")
            shutil.move(task_file, destination)
            # Create a result file indicating validation failure
            result_data = {
                "task_id": task_id, "processed_time": datetime.now().isoformat(),
                "success": False, "message": f"Validation Failed: {message}"
            }
            result_file_name = Path(task_file).stem + "_result.json"
            result_file = os.path.join(taskshistory_dir, result_file_name)
            with open(result_file, 'w') as f: json.dump(result_data, f, indent=2)
            return False
        
        logger.info(f"Task {task_id} validated successfully. Type: {task_data['segmentation_type']}")
        success, result_message = run_vista3d_task(task_data, config)
        
        # Define output paths for result file
        output_mask_path = os.path.join(task_data.get('output_directory', './'), "ct_seg.nii.gz")
        output_labels_path = os.path.join(task_data.get('output_directory', './'), "ct_seg.json")
        
        # Check if output files actually exist if success is True
        if success:
            if not os.path.exists(output_mask_path):
                logger.warning(f"Segmentation reported success for task {task_id}, but output mask {output_mask_path} not found.")
                # success = False # Optionally mark as failed if output is critical
                # result_message += " (Output mask missing)"
            if task_data["segmentation_type"] == "point" and not os.path.exists(output_labels_path):
                 logger.warning(f"Segmentation reported success for task {task_id}, but ROI file {output_labels_path} not found for point-based type.")


        result_data = {
            "task_id": task_id,
            "processed_time": datetime.now().isoformat(),
            "success": success,
            "message": result_message,
            "output_mask": output_mask_path if os.path.exists(output_mask_path) else None,
            "output_labels": output_labels_path if task_data["segmentation_type"] == "point" and os.path.exists(output_labels_path) else None
        }
        
        result_file_name = Path(task_file).stem + "_result.json"
        result_file = os.path.join(taskshistory_dir, result_file_name)
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        destination = os.path.join(taskshistory_dir, f"{os.path.basename(task_file)}")
        shutil.move(task_file, destination)
        
        if success:
            logger.info(f"Task {task_id} completed successfully. Results in {result_file}")
        else:
            logger.error(f"Task {task_id} failed: {result_message}. Results in {result_file}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error processing task file {task_file}: {str(e)}")
        logger.error(traceback.format_exc())
        task_id_fallback = Path(task_file).stem
        destination = os.path.join(taskshistory_dir, f"error_processing_{os.path.basename(task_file)}")
        try:
            shutil.move(task_file, destination)
        except Exception as move_err:
            logger.error(f"Could not move errored task file {task_file} to history: {move_err}")

        # Create a result file indicating processing error
        result_data = {
            "task_id": task_data.get("task_id", task_id_fallback) if 'task_data' in locals() else task_id_fallback,
            "processed_time": datetime.now().isoformat(),
            "success": False, "message": f"Unhandled error during task processing: {str(e)}"
        }
        result_file_name = Path(task_file).stem + "_result.json"
        result_file = os.path.join(taskshistory_dir, result_file_name)
        try:
            with open(result_file, 'w') as f: json.dump(result_data, f, indent=2)
        except Exception as res_err:
             logger.error(f"Could not write result file for errored task {task_file}: {res_err}")
        return False

def monitor_tasks_folder(tasks_dir, taskshistory_dir, interval=5, config=None):
    """Monitor tasks folder for new task files."""
    logger.info(f"Starting VISTA3D service. Monitoring {tasks_dir} every {interval} seconds")
    
    while True:
        try:
            task_files = [os.path.join(tasks_dir, f) for f in os.listdir(tasks_dir) if f.endswith('.tsk')]
            
            if task_files:
                logger.info(f"Found {len(task_files)} task(s): {', '.join(os.path.basename(f) for f in task_files)}")
                for task_file in sorted(task_files): # Process in sorted order (e.g., by name/timestamp)
                    if os.path.exists(task_file): # Check if still exists (might be processed by another instance if not careful)
                        process_task_file(task_file, taskshistory_dir, config)
                    else:
                        logger.warning(f"Task file {task_file} disappeared before processing, likely handled by another process or moved.")
            
            time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
        
        except Exception as e:
            logger.error(f"Critical error in monitoring loop: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(interval * 5) # Longer sleep on critical error

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="VISTA3D Service")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--base_dir", help="Base directory for service files (overrides config)")
    parser.add_argument("--interval", type=int, help="Interval in seconds to check for new tasks (overrides config)")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    base_dir = args.base_dir if args.base_dir else config.get("service", {}).get("base_directory", "./vista_service")
    interval = args.interval if args.interval else config.get("service", {}).get("check_interval", 30)
    
    tasks_dir, taskshistory_dir = setup_folders(base_dir, config)
    
    monitor_tasks_folder(tasks_dir, taskshistory_dir, interval, config)
    
    return 0

if __name__ == "__main__":
    # Ensure dependencies are checked early if critical
    if torch is None or np is None or nib is None:
        logger.warning("One or more core dependencies (PyTorch, NumPy, Nibabel) are missing. "
                       "Service functionality will be limited, 'point' mode will fail validation.")
        # sys.exit("Core dependencies missing. Please install PyTorch, NumPy, and Nibabel.") # Optionally exit
    
    sys.exit(main())