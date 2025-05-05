#!/usr/bin/env python
"""
VISTA3D Task Creator
===================

Utility to create task files for the VISTA3D service.

Usage:
    python create_task.py --input "path/to/ct.nii.gz" --output "path/to/output" --type "point" --point "175,136,141" --label 1
    python create_task.py --input "path/to/ct.nii.gz" --output "path/to/output" --type "full"
"""

import os
import json
import uuid
import argparse
from datetime import datetime

def create_task_file(args):
    """Create a task file based on command line arguments."""
    # Generate task ID if not provided
    if not args.task_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.task_id = f"task_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    # Create task data
    task_data = {
        "task_id": args.task_id,
        "input_file": args.input,
        "output_directory": args.output,
        "segmentation_type": args.type,
        "description": args.description
    }
    
    # Add point-specific data if needed
    if args.type == "point":
        if not args.point:
            raise ValueError("Point coordinates must be provided for point-based segmentation")
        if not args.label:
            raise ValueError("Label must be provided for point-based segmentation")
        
        # Parse point coordinates
        point_coords = [float(x) for x in args.point.split(",")]
        if len(point_coords) != 3:
            raise ValueError("Point coordinates must be in format 'x,y,z'")
        
        task_data["point_coordinates"] = point_coords
        task_data["label"] = args.label
    
    # Create tasks directory if it doesn't exist
    os.makedirs(args.tasks_dir, exist_ok=True)
    
    # Write task file
    task_file = os.path.join(args.tasks_dir, f"{args.task_id}.json")
    with open(task_file, 'w') as f:
        json.dump(task_data, f, indent=2)
    
    print(f"Task file created: {task_file}")
    return task_file

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="VISTA3D Task Creator")
    parser.add_argument("--task_id", help="Unique task identifier (generated if not provided)")
    parser.add_argument("--input", required=True, help="Input CT scan file")
    parser.add_argument("--output", required=True, help="Output directory for segmentation results")
    parser.add_argument("--type", choices=["full", "point"], default="full", help="Segmentation type")
    parser.add_argument("--point", help="Point coordinates (x,y,z) for point-based segmentation")
    parser.add_argument("--label", type=int, help="Label for point-based segmentation")
    parser.add_argument("--description", help="Task description")
    parser.add_argument("--tasks_dir", default="./vista_service/tasks", help="Directory to save task files")
    
    args = parser.parse_args()
    create_task_file(args)
    
    return 0

if __name__ == "__main__":
    main()
