#!/usr/bin/env python
"""
Batch Processing Script for Totalsegmentator Dataset with VISTA3D

This script:
1. Finds all CT scans in the Totalsegmentator dataset
2. Creates VISTA3D segmentation tasks for a subset of them
3. Organizes results for comparison
"""

import os
import json
import argparse
import random
import time
from pathlib import Path
import shutil
from datetime import datetime

def find_ct_scans(base_dir):
    """Find all CT scan files in the Totalsegmentator dataset."""
    ct_files = []
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "ct.nii.gz":
                ct_files.append(os.path.join(root, file))
    
    print(f"Found {len(ct_files)} CT scans in {base_dir}")
    return ct_files

def create_task_file(task_id, input_file, output_dir, seg_type="full", point=None, label=None, description=None):
    """Create a task file for VISTA3D service."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create task data
    task_data = {
        "task_id": task_id,
        "input_file": input_file,
        "output_directory": output_dir,
        "segmentation_type": seg_type,
        "description": description or f"Segmentation of {os.path.basename(os.path.dirname(input_file))}"
    }
    
    # Add point-based parameters if needed
    if seg_type == "point" and point and label:
        task_data["point_coordinates"] = point
        task_data["label"] = label
    
    # Create tasks directory if it doesn't exist
    tasks_dir = os.path.join("vista_service", "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    
    # Generate unique task filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_filename = os.path.join(tasks_dir, f"task_{timestamp}_{task_id}.json")
    
    # Write task file
    with open(task_filename, "w") as f:
        json.dump(task_data, f, indent=4)
    
    return task_filename

def batch_process(ct_files, count, output_base_dir, seg_type="full", wait_time=0):
    """Process a batch of CT scans with VISTA3D."""
    # Select subset if needed
    if count < len(ct_files):
        selected_files = random.sample(ct_files, count)
    else:
        selected_files = ct_files
    
    print(f"Processing {len(selected_files)} CT scans...")
    
    # Create tasks for each selected file
    for i, ct_file in enumerate(selected_files):
        # Get folder name (e.g., s0031)
        folder_name = os.path.basename(os.path.dirname(ct_file))
        
        # Create output directory
        output_dir = os.path.join(output_base_dir, folder_name)
        
        # Create unique task ID
        task_id = f"{folder_name}_{seg_type}"
        
        # Create task file
        task_file = create_task_file(
            task_id=task_id,
            input_file=ct_file,
            output_dir=output_dir,
            seg_type=seg_type,
            description=f"{seg_type.capitalize()} segmentation of {folder_name}"
        )
        
        print(f"[{i+1}/{len(selected_files)}] Created task: {task_file}")
        
        # Optional wait time between task creation to avoid overwhelming the service
        if wait_time > 0 and i < len(selected_files) - 1:
            print(f"Waiting {wait_time} seconds before creating next task...")
            time.sleep(wait_time)
    
    print(f"Created {len(selected_files)} tasks. The VISTA3D service will process them automatically.")
    print(f"Results will be saved to: {output_base_dir}")

def create_comparison_script(output_base_dir):
    """Create a script to help compare the segmentation results."""
    script_path = os.path.join(output_base_dir, "compare_results.py")
    
    script_content = """#!/usr/bin/env python
\"\"\"
Comparison Script for VISTA3D Segmentation Results

This script helps analyze and compare segmentation results from VISTA3D.
\"\"\"

import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd

def load_segmentation(file_path):
    \"\"\"Load a segmentation file and return the data.\"\"\"
    if os.path.exists(file_path):
        nii = nib.load(file_path)
        return nii.get_fdata()
    return None

def count_labels(seg_data):
    \"\"\"Count the number of voxels for each label.\"\"\"
    if seg_data is None:
        return {}
    
    unique, counts = np.unique(seg_data, return_counts=True)
    return dict(zip(unique, counts))

def analyze_directory(base_dir):
    \"\"\"Analyze all segmentation results in the directory.\"\"\"
    results = []
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".nii.gz") and "seg" in file:
                seg_path = os.path.join(root, file)
                case_id = os.path.basename(os.path.dirname(seg_path))
                
                # Load segmentation
                seg_data = load_segmentation(seg_path)
                
                if seg_data is not None:
                    # Get label counts
                    label_counts = count_labels(seg_data)
                    
                    # Calculate total segmented voxels
                    total_segmented = sum(count for label, count in label_counts.items() if label > 0)
                    
                    # Get file size
                    file_size_mb = os.path.getsize(seg_path) / (1024 * 1024)
                    
                    # Add to results
                    results.append({
                        "case_id": case_id,
                        "file_path": seg_path,
                        "file_size_mb": file_size_mb,
                        "total_segmented_voxels": total_segmented,
                        "num_labels": len(label_counts) - (1 if 0 in label_counts else 0),
                        "label_counts": label_counts
                    })
    
    return results

def generate_report(results, output_file):
    \"\"\"Generate a CSV report of the analysis results.\"\"\"
    # Create DataFrame
    df = pd.DataFrame([
        {
            "case_id": r["case_id"],
            "file_size_mb": r["file_size_mb"],
            "total_segmented_voxels": r["total_segmented_voxels"],
            "num_labels": r["num_labels"]
        }
        for r in results
    ])
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Report saved to: {output_file}")
    
    return df

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Analyzing segmentation results in: {base_dir}")
    
    # Analyze results
    results = analyze_directory(base_dir)
    
    if results:
        # Generate report
        report_file = os.path.join(base_dir, "segmentation_report.csv")
        df = generate_report(results, report_file)
        
        # Print summary
        print(f"\\nAnalyzed {len(results)} segmentation files")
        print(f"Average file size: {df['file_size_mb'].mean():.2f} MB")
        print(f"Average number of labels: {df['num_labels'].mean():.2f}")
        print(f"Average segmented voxels: {df['total_segmented_voxels'].mean():.2f}")
    else:
        print("No segmentation files found.")

if __name__ == "__main__":
    main()
"""
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    print(f"Created comparison script: {script_path}")
    return script_path

def main():
    parser = argparse.ArgumentParser(description="Batch process Totalsegmentator dataset with VISTA3D")
    parser.add_argument("--dataset", type=str, default="C:\\Users\\Albert\\Totalsegmentator_dataset_v201",
                        help="Path to Totalsegmentator dataset")
    parser.add_argument("--output", type=str, default="C:\\Users\\Albert\\output\\batch_totalsegmentator",
                        help="Base output directory for results")
    parser.add_argument("--count", type=int, default=100,
                        help="Number of CT scans to process (default: 100)")
    parser.add_argument("--type", type=str, choices=["full", "point"], default="full",
                        help="Segmentation type (default: full)")
    parser.add_argument("--wait", type=int, default=0,
                        help="Wait time in seconds between task creation (default: 0)")
    
    args = parser.parse_args()
    
    # Find all CT scans
    ct_files = find_ct_scans(args.dataset)
    
    if not ct_files:
        print(f"No CT scans found in {args.dataset}")
        return
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Process batch
    batch_process(ct_files, args.count, args.output, args.type, args.wait)
    
    # Create comparison script
    create_comparison_script(args.output)
    
    print("\nBatch processing setup complete!")
    print("The VISTA3D service will process the tasks automatically.")
    print(f"After processing is complete, run the comparison script: {os.path.join(args.output, 'compare_results.py')}")

if __name__ == "__main__":
    main()
