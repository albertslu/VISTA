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
import threading # For Lock
from concurrent.futures import ThreadPoolExecutor
import monai
import threading

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
                "check_interval": 1,
                "log_file": "vista_service.log",
                "max_concurrent_tasks": 5
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
    
    segmentation_type = task_data.get("segmentation_type", "point")
    task_data["segmentation_type"] = segmentation_type

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
    try:
        if torch is None: 
            logger.warning("PyTorch not available, defaulting to CPU for device selection logic.")
            return "cpu"

        if device_preference != "auto" and device_preference.startswith("cuda"):
            try:
                device = torch.device(device_preference)
                test_tensor = torch.zeros(1, device=device)
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
    except ImportError:
        logger.warning("PyTorch not available, defaulting to CPU")
    
    logger.info("Using CPU device")
    return "cpu"

def _get_roi_center_physical(prompt_spec):
    """
    Retrieves 'physical_center_of_box' from the prompt_spec.
    Returns the center if valid (list of 3 numbers), otherwise None.
    """
    physical_center = prompt_spec.get("physical_center_of_box")
    if isinstance(physical_center, list) and len(physical_center) == 3:
        if all(isinstance(c, (int, float)) for c in physical_center):
            return physical_center
        else:
            logger.warning(f"Invalid data types in 'physical_center_of_box' for prompt targeting {prompt_spec.get('target_output_label', 'Unknown')}. Expected numbers.")
            return None
    if physical_center is not None: # It exists but is not the expected format
         logger.warning(f"Malformed 'physical_center_of_box' for prompt targeting {prompt_spec.get('target_output_label', 'Unknown')}. Expected list of 3 numbers.")
    return None

def _centers_are_close(center1, center2, tolerance=1e-3):
    if center1 is None or center2 is None or not isinstance(center1, list) or not isinstance(center2, list) or len(center1) != 3 or len(center2) != 3:
        return False
    return np.allclose(np.array(center1), np.array(center2), atol=tolerance)

def run_vista3d_task(task_data, config):
    """Run VISTA3D segmentation based on task specifications."""
    from vista3d.scripts.infer import InferClass, EVERYTHING_PROMPT
    
    os.makedirs(task_data["output_directory"], exist_ok=True)
    device = get_optimal_device(config["vista3d"]["device"])
    
    logger.info(f"Using config file for inference: {config["vista3d"]["config_file"]}")

    infer_obj = InferClass(
        config_file=config["vista3d"]["config_file"],
        device=device
    )
    
    try:
        segmentation_type = task_data["segmentation_type"]

        if segmentation_type == "point":
            if not all([torch, np, nib]):
                 return False, "Cannot run 'point': PyTorch, NumPy or Nibabel missing."
            
            vista_roi_path = os.path.join(task_data["output_directory"], "ct_seg.json")
            output_mask_file = os.path.join(task_data["output_directory"], "ct_seg.nii.gz")

            existing_rois_map = {}
            if os.path.exists(vista_roi_path):
                try:
                    with open(vista_roi_path, 'r') as f_exist:
                        existing_data = json.load(f_exist)
                    if "rois" in existing_data and isinstance(existing_data["rois"], list):
                        for roi_entry in existing_data["rois"]:
                            if "ROIIndex" in roi_entry:
                                existing_rois_map[roi_entry["ROIIndex"]] = roi_entry
                    logger.info(f"Loaded {len(existing_rois_map)} existing ROIs from {vista_roi_path}")
                except Exception as e:
                    logger.warning(f"Could not load existing {vista_roi_path}: {e}. Will proceed as if it's new.")

            prompts_to_process = []
            all_current_task_prompt_details = [] 

            for i, prompt_spec in enumerate(task_data.get("segmentation_prompts", [])):
                target_label = prompt_spec["target_output_label"]
                center_from_current_task_prompt = _get_roi_center_physical(prompt_spec)
                all_current_task_prompt_details.append({
                    'prompt_spec': prompt_spec, 
                    'physical_center_from_task': center_from_current_task_prompt
                })

                existing_roi_entry = existing_rois_map.get(target_label)
                existing_center_in_json = None
                if existing_roi_entry:
                    existing_center_in_json = existing_roi_entry.get("ROICenter")

                if center_from_current_task_prompt is None:
                    logger.info(f"Prompt for label {target_label} needs processing ('physical_center_of_box' missing or invalid in current task).")
                    prompts_to_process.append(prompt_spec)
                elif not _centers_are_close(center_from_current_task_prompt, existing_center_in_json):
                    logger.info(f"Prompt for label {target_label} needs processing (center changed or new). Task center: {center_from_current_task_prompt}, Existing JSON center: {existing_center_in_json}")
                    prompts_to_process.append(prompt_spec)
                else:
                    logger.info(f"Skipping segmentation for label {target_label}, task center {center_from_current_task_prompt} matches existing JSON center.")

            segmentation_results_new = [] 
            first_processed_mask_metadata = None

            if prompts_to_process:
                logger.info(f"Running point-based segmentation for {len(prompts_to_process)} target labels.")
                for prompt_spec in prompts_to_process:
                    target_label = prompt_spec["target_output_label"]
                    positive_points = prompt_spec.get("positive_points", [])
                    negative_points = prompt_spec.get("negative_points", [])
                    display_name = prompt_spec.get("display_name", f"Label {target_label}")
                    
                    current_points = positive_points + negative_points
                    if not current_points: 
                        logger.warning(f"No points for target_label {target_label} in processing list. Skipping.")
                        continue

                    current_point_types = [1] * len(positive_points) + [0] * len(negative_points)
                    logger.info(f"Processing target_label: {target_label} with {len(positive_points)} pos, {len(negative_points)} neg points for segmentation.")
                    
                    if hasattr(infer_obj, 'clear_cache') and callable(infer_obj.clear_cache):
                        infer_obj.clear_cache()

                    result_tensor = infer_obj.infer(
                        image_file=task_data["input_file"],
                        point=current_points,
                        point_label=current_point_types,
                        prompt_class=[target_label], 
                        save_mask=False
                    )
                    
                    if result_tensor is not None:
                        segmentation_results_new.append({
                            "label_id": target_label,
                            "mask_tensor": result_tensor.cpu(), 
                            "display_name": display_name 
                        })
                        if first_processed_mask_metadata is None and hasattr(result_tensor, 'affine') and hasattr(result_tensor, 'shape'):
                            first_processed_mask_metadata = {
                                'affine': result_tensor.affine.cpu().numpy() if hasattr(result_tensor.affine, 'cpu') else result_tensor.affine,
                                'shape': result_tensor.shape 
                            }
                    else:
                        logger.warning(f"Inference failed for target_label: {target_label}")
            else:
                logger.info("No prompts require new segmentation processing.")

            # Mask Combination
            final_combined_mask_tensor = None
            final_mask_affine = None
            final_mask_shape_3d = None

            if os.path.exists(output_mask_file):
                try:
                    existing_mask_nii = nib.load(output_mask_file)
                    final_combined_mask_tensor = torch.from_numpy(existing_mask_nii.get_fdata().astype(np.int16))
                    final_mask_affine = existing_mask_nii.affine
                    final_mask_shape_3d = final_combined_mask_tensor.shape
                    logger.info(f"Loaded existing mask {output_mask_file} for merging.")
                except Exception as e:
                    logger.warning(f"Could not load existing mask {output_mask_file}: {e}. Will try to create new if needed.")

            if segmentation_results_new: 
                if final_combined_mask_tensor is None: 
                    if first_processed_mask_metadata:
                        raw_shape = first_processed_mask_metadata['shape'] 
                        final_mask_shape_3d = raw_shape[1:] if len(raw_shape) == 4 and raw_shape[0] == 1 else raw_shape
                        final_combined_mask_tensor = torch.zeros(final_mask_shape_3d, dtype=torch.int16)
                        final_mask_affine = first_processed_mask_metadata['affine']
                        logger.info(f"Initialized new empty mask with shape {final_mask_shape_3d}.")
                    else:
                        logger.error("New segmentations produced, but no metadata to create a base mask and no existing mask found.")
                        return False, "Failed to establish mask geometry for new segmentations."

                if final_combined_mask_tensor is not None:
                    for seg_res in segmentation_results_new:
                        label_id = seg_res["label_id"]
                        mask_tensor = seg_res["mask_tensor"] 
                        
                        squeezed_mask = mask_tensor.squeeze(0) 
                        if squeezed_mask.shape != final_mask_shape_3d:
                            logger.warning(f"Shape mismatch for label {label_id}: mask {squeezed_mask.shape}, base {final_mask_shape_3d}. Skipping merge for this label.")
                            continue

                        binary_class_mask = (squeezed_mask > 0.5).long()
                        
                        final_combined_mask_tensor[final_combined_mask_tensor == label_id] = 0
                        final_combined_mask_tensor[binary_class_mask == 1] = label_id
                        logger.info(f"Merged segmentation for label {label_id} into combined mask.")
            
            if final_combined_mask_tensor is not None and final_mask_affine is not None:
                nifti_img = nib.Nifti1Image(final_combined_mask_tensor.numpy().astype(np.int16), final_mask_affine)
                nib.save(nifti_img, output_mask_file)
                logger.info(f"Saved combined multi-label segmentation to: {output_mask_file}")
            elif not segmentation_results_new and os.path.exists(output_mask_file):
                logger.info(f"No new segmentations. Existing mask {output_mask_file} remains unchanged.")
            elif not os.path.exists(output_mask_file) and not segmentation_results_new:
                 logger.info("No existing mask and no new segmentations produced. No mask file saved/updated.")
            else:
                logger.info("No segmentation mask to save (e.g. no new results and no existing mask, or geometry issue).")


            # Generate ct_seg.json
            rois_for_current_task = []
            for detail in all_current_task_prompt_details:
                prompt_spec = detail['prompt_spec']
                target_label = prompt_spec["target_output_label"]
                display_name = prompt_spec.get("display_name", f"Label {target_label}")
                rois_for_current_task.append({
                    "ROIIndex": target_label,
                    "ROIName": display_name,
                    "ROICenter": detail['physical_center_from_task'], 
                    "visible": True 
                })
            
            roi_colors = [
                [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.5, 0.5, 1.0],
                [0.0, 0.5, 1.0], [1.0, 0.5, 1.0], [1.0, 0.5, 0.0], [0.2, 0.5, 0.2],
                [0.2, 0.8, 0.4], [1.0, 0.0, 0.5], [0.5, 0.0, 0.0], [0.0, 0.5, 0.0],
                [1.0, 0.0, 0.5], [0.0, 0.5, 0.5], [0.5, 0.0, 1.0], [1.0, 0.2, 0.2],
                [0.7, 0.7, 0.0], [0.2, 0.2, 0.7], [0.0, 0.7, 0.7], [0.7, 0.0, 0.7],
                [0.7, 0.5, 0.2], [0.4, 0.7, 0.2], [0.8, 0.2, 0.8], [0.8, 0.8, 0.2],
                [0.2, 0.8, 0.8], [0.8, 0.2, 0.2], [0.5, 0.2, 0.7], [0.7, 0.5, 0.7],
                [0.5, 0.7, 0.2], [0.2, 0.7, 0.5], [0.7, 0.2, 0.5]
            ]
            
            num_prompts_in_task = len(task_data.get("segmentation_prompts", []))
            final_json_content_rois = []

            if num_prompts_in_task == 1:
                final_json_content_rois = list(rois_for_current_task) 
                logger.info(f"Single prompt task: {vista_roi_path} will be overwritten with this prompt's ROI info.")
            else: 
                final_json_content_rois = list(rois_for_current_task) 
                current_task_labels_set = {roi['ROIIndex'] for roi in rois_for_current_task}
                
                for label_idx, existing_roi_entry in existing_rois_map.items():
                    if label_idx not in current_task_labels_set:
                        final_json_content_rois.append(existing_roi_entry)
                logger.info(f"Multiple/zero prompts task: Merged/formed {len(final_json_content_rois)} ROIs for {vista_roi_path}.")

            final_json_content_rois.sort(key=lambda r: r['ROIIndex']) 
            unique_labels_in_final_json = [r['ROIIndex'] for r in final_json_content_rois]

            for roi_entry in final_json_content_rois:
                try:
                    color_idx = unique_labels_in_final_json.index(roi_entry['ROIIndex'])
                    roi_entry['ROIColor'] = roi_colors[color_idx % len(roi_colors)]
                except ValueError:
                    logger.warning(f"Could not find ROIIndex {roi_entry['ROIIndex']} in unique_labels_in_final_json for color assignment. Using default.")
                    roi_entry['ROIColor'] = [0.5, 0.5, 0.5]


            with open(vista_roi_path, 'w') as f_final_roi:
                json.dump({"rois": final_json_content_rois}, f_final_roi, indent=2)
            logger.info(f"Saved/Updated final VISTA ROI info to: {vista_roi_path}")

            return True, "Point segmentation completed successfully."
        
        else: # Full segmentation
            logger.info(f"Running full segmentation with {len(EVERYTHING_PROMPT)} labels")
            result = infer_obj.infer(
                image_file=task_data["input_file"],
                save_mask=True, 
                label_prompt=EVERYTHING_PROMPT 
            )
            if result is not None:
                output_file = os.path.join(task_data["output_directory"], "ct_seg.nii.gz")
                logger.info(f"Saving full segmentation to: {output_file}")
                
                result_np = result.cpu().numpy().astype(np.float32) 
                nifti_img = nib.Nifti1Image(result_np[0], result.affine.cpu().numpy() if hasattr(result, 'affine') else np.eye(4))
                nib.save(nifti_img, output_file)
                
                if os.path.exists(output_file):
                    logger.info(f"Full segmentation saved successfully")
                    return True, "Full segmentation completed successfully."
                else:
                    return False, "Failed to save full segmentation."
            else:
                return False, "Full inference failed to produce valid output."
    
    except Exception as e:
        logger.error(f"Error during VISTA3D task execution: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

def process_task_file(task_file_path_submitted, taskshistory_dir, config, active_task_paths, active_task_paths_lock):
    """Process a single task file."""
    task_file = task_file_path_submitted 
    try:
        with open(task_file, 'r') as f:
            task_data = json.load(f)
        
        task_id = task_data.get("task_id", os.path.basename(task_file))
        logger.info(f"Processing Task ID: {task_id}, File: {task_file}")
        
        valid, message = validate_task(task_data)
        if not valid:
            logger.error(f"Task validation failed for {task_id}: {message}")
            destination = os.path.join(taskshistory_dir, f"failed_validation_{os.path.basename(task_file)}")
            shutil.move(task_file, destination)
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
        
        output_mask_path = os.path.join(task_data.get('output_directory', './'), "ct_seg.nii.gz")
        output_labels_path = os.path.join(task_data.get('output_directory', './'), "ct_seg.json")
        
        if success:
            if not os.path.exists(output_mask_path) and task_data["segmentation_type"] != "point": # For "full" seg, mask must exist
                 logger.warning(f"Segmentation reported success for task {task_id} (type: {task_data['segmentation_type']}), but output mask {output_mask_path} not found.")
            # For "point" type, mask might not be updated if no new segs, so existence isn't strictly a failure if success=True
            if task_data["segmentation_type"] == "point" and not os.path.exists(output_labels_path):
                 logger.warning(f"Segmentation reported success for task {task_id}, but ROI file {output_labels_path} not found for point-based type.")


        result_data = {
            "task_id": task_id,
            "processed_time": datetime.now().isoformat(),
            "success": success,
            "message": result_message,
            "output_mask": output_mask_path if os.path.exists(output_mask_path) else None,
            "output_labels": output_labels_path if os.path.exists(output_labels_path) else None # Always report if it exists
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
    finally:
        with active_task_paths_lock:
            if task_file_path_submitted in active_task_paths:
                active_task_paths.remove(task_file_path_submitted)
                logger.info(f"Task {os.path.basename(task_file_path_submitted)} processing complete, removed from active set.")


def monitor_tasks_folder(tasks_dir, taskshistory_dir, interval=5, config=None, max_concurrent_tasks=1):
    """Monitor tasks folder for new task files."""
    logger.info(
        f"Starting VISTA3D service. Monitoring {tasks_dir} every {interval} seconds. "
        f"Max concurrent tasks: {max_concurrent_tasks}"
    )

    active_task_paths = set()
    active_task_paths_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_concurrent_tasks) as executor:
        try:
            while True:
                try:
                    discovered_task_files = [
                        os.path.join(tasks_dir, f)
                        for f in os.listdir(tasks_dir)
                        if f.endswith('.tsk')
                    ]

                    if discovered_task_files:
                        logger.debug(f"Discovered {len(discovered_task_files)} .tsk files. Checking against active set.")
                        for task_path in sorted(discovered_task_files):
                            if not os.path.exists(task_path): 
                                continue

                            with active_task_paths_lock:
                                if task_path in active_task_paths:
                                    logger.debug(f"Task {os.path.basename(task_path)} is already active. Skipping.")
                                    continue
                                active_task_paths.add(task_path)
                                logger.info(f"Task {os.path.basename(task_path)} added to active set for submission.")
                            
                            try:
                                logger.info(f"Submitting task {os.path.basename(task_path)} to executor.")
                                executor.submit(process_task_file, task_path, taskshistory_dir, config, active_task_paths, active_task_paths_lock)
                            except Exception as e_submit:
                                logger.error(f"Failed to submit task {os.path.basename(task_path)} to executor: {e_submit}")
                                with active_task_paths_lock:
                                    if task_path in active_task_paths: 
                                        active_task_paths.remove(task_path)
                                        logger.info(f"Removed {os.path.basename(task_path)} from active set due to submission failure.")
                    
                    time.sleep(interval)
                
                except KeyboardInterrupt:
                    logger.info("Service stopping... waiting for tasks to complete.")
                    break 
                
                except Exception as e:
                    logger.error(f"Critical error in monitoring loop: {str(e)}")
                    logger.error(traceback.format_exc())
                    time.sleep(interval * 5) 
        finally:
            logger.info("VISTA3D service shutting down executor.")
    logger.info("VISTA3D service monitor loop ended.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="VISTA3D Service")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--base_dir", help="Base directory for service files (overrides config)")
    parser.add_argument("--interval", type=int, help="Interval in seconds to check for new tasks (overrides config)")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    base_dir = args.base_dir if args.base_dir else config.get("service", {}).get("base_directory", "./vista_service")
    interval = args.interval if args.interval else config.get("service", {}).get("check_interval", 1)
    max_concurrent_tasks = config.get("service", {}).get("max_concurrent_tasks", 5)
    
    tasks_dir, taskshistory_dir = setup_folders(base_dir, config)
    
    monitor_tasks_folder(tasks_dir, taskshistory_dir, interval, config, max_concurrent_tasks)
    
    return 0

if __name__ == "__main__":
    if torch is None or np is None or nib is None:
        logger.warning("One or more core dependencies (PyTorch, NumPy, Nibabel) are missing. "
                       "Service functionality will be limited, 'point' mode will fail validation if not all are present.")
    
    sys.exit(main())