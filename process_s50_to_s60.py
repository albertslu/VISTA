#!/usr/bin/env python
"""
Process CT scans from s0050 to s0060 with VISTA3D

This script:
1. Creates VISTA3D segmentation tasks for scans s0050 through s0060
2. Submits them to the VISTA3D service
3. Organizes results for comparison
"""

import os
import json
import time
from datetime import datetime
import shutil

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

def process_specific_range(start_num, end_num, base_dir, output_base_dir, seg_type="full", wait_time=5):
    """Process CT scans from s00XX to s00YY."""
    processed_count = 0
    
    for i in range(start_num, end_num + 1):
        # Format folder name with leading zeros
        folder_name = f"s{i:04d}"
        folder_path = os.path.join(base_dir, folder_name)
        
        # Check if folder exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist, skipping...")
            continue
        
        # Check if CT file exists
        ct_file = os.path.join(folder_path, "ct.nii.gz")
        if not os.path.exists(ct_file):
            print(f"CT file not found in {folder_path}, skipping...")
            continue
        
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
        
        print(f"[{processed_count+1}] Created task for {folder_name}: {task_file}")
        processed_count += 1
        
        # Optional wait time between task creation to avoid overwhelming the service
        if wait_time > 0 and i < end_num:
            print(f"Waiting {wait_time} seconds before creating next task...")
            time.sleep(wait_time)
    
    print(f"\nCreated {processed_count} tasks. The VISTA3D service will process them automatically.")
    print(f"Results will be saved to: {output_base_dir}")
    return processed_count

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
    # Configuration
    base_dir = "C:\\Users\\Albert\\Totalsegmentator_dataset_v201"
    output_base_dir = "C:\\Users\\Albert\\output\\s50_to_s60_results"
    start_num = 50
    end_num = 60
    seg_type = "full"
    wait_time = 5  # seconds between task creation
    
    # Create output directory
    os.makedirs(output_base_dir, exist_ok=True)
    
    print(f"Processing CT scans from s{start_num:04d} to s{end_num:04d}...")
    
    # Process specific range
    count = process_specific_range(start_num, end_num, base_dir, output_base_dir, seg_type, wait_time)
    
    if count > 0:
        # Create comparison script
        create_comparison_script(output_base_dir)
        
        print("\nProcessing setup complete!")
        print("The VISTA3D service will process the tasks automatically.")
        print(f"After processing is complete, run the comparison script: {os.path.join(output_base_dir, 'compare_results.py')}")
    else:
        print("No tasks were created. Please check the folder paths and try again.")

if __name__ == "__main__":
    main()
