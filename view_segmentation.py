#!/usr/bin/env python3
"""
VISTA3D Segmentation Viewer
Loads a NIfTI segmentation file and displays basic statistics and content information.
"""

import os
import sys
import numpy as np
import argparse
import matplotlib.pyplot as plt
from pathlib import Path

try:
    import nibabel as nib
except ImportError:
    print("Error: nibabel library not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nibabel"])
    import nibabel as nib

def load_segmentation(file_path):
    """Load NIfTI segmentation file and return the data array."""
    try:
        # Load the NIfTI file
        nii_img = nib.load(file_path)
        
        # Get the data as a numpy array
        data = nii_img.get_fdata()
        
        return data, nii_img
    except Exception as e:
        print(f"Error loading segmentation file: {str(e)}")
        sys.exit(1)

def analyze_segmentation(data):
    """Analyze segmentation data and print statistics."""
    # Basic statistics
    total_voxels = data.size
    nonzero_voxels = np.count_nonzero(data)
    nonzero_percentage = (nonzero_voxels / total_voxels) * 100
    
    print(f"Total voxels: {total_voxels:,}")
    print(f"Non-zero voxels: {nonzero_voxels:,} ({nonzero_percentage:.2f}%)")
    
    if nonzero_voxels == 0:
        print("\nWARNING: Segmentation is completely empty (all zeros).")
        print("Possible reasons:")
        print("  1. The inference process failed or produced no output")
        print("  2. The input image might not contain any recognizable structures")
        print("  3. There could be file format or compatibility issues")
        return False
    
    # Get unique label values (skipping 0 background)
    unique_labels = np.unique(data)
    nonzero_labels = unique_labels[unique_labels > 0]
    
    print(f"\nNumber of unique labels: {len(nonzero_labels)}")
    print(f"Label values: {nonzero_labels}")
    
    # Count voxels for each label
    label_counts = {}
    for label in nonzero_labels:
        count = np.sum(data == label)
        label_counts[label] = count
    
    # Sort labels by count (descending)
    sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTop 10 most common labels:")
    for i, (label, count) in enumerate(sorted_labels[:10], 1):
        percentage = (count / nonzero_voxels) * 100
        print(f"  {i}. Label {int(label)}: {count:,} voxels ({percentage:.2f}%)")
    
    return True

def visualize_segmentation(data, output_dir):
    """Create simple visualizations of the segmentation data."""
    if np.count_nonzero(data) == 0:
        print("Skipping visualization - no segmentation data found.")
        return
    
    # Get the middle slices for each axis
    x_mid = data.shape[0] // 2
    y_mid = data.shape[1] // 2
    z_mid = data.shape[2] // 2
    
    # Create a figure with 3 subplots (one for each orthogonal plane)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Axial view (top-down)
    axes[0].imshow(data[x_mid, :, :].T, cmap='viridis')
    axes[0].set_title(f'Axial Slice (X={x_mid})')
    
    # Coronal view (front-back)
    axes[1].imshow(data[:, y_mid, :].T, cmap='viridis')
    axes[1].set_title(f'Coronal Slice (Y={y_mid})')
    
    # Sagittal view (side)
    axes[2].imshow(data[:, :, z_mid].T, cmap='viridis')
    axes[2].set_title(f'Sagittal Slice (Z={z_mid})')
    
    for ax in axes:
        ax.set_aspect('equal')
        ax.axis('off')
    
    plt.tight_layout()
    
    # Save figure
    output_file = os.path.join(output_dir, "segmentation_overview.png")
    plt.savefig(output_file)
    print(f"\nVisualization saved to: {output_file}")

def find_nonzero_slices(data):
    """Find slices that contain non-zero data in each dimension."""
    if np.count_nonzero(data) == a0:
        return None
    
    # Check each axis
    nonzero_x = [i for i in range(data.shape[0]) if np.any(data[i, :, :])]
    nonzero_y = [i for i in range(data.shape[1]) if np.any(data[:, i, :])]
    nonzero_z = [i for i in range(data.shape[2]) if np.any(data[:, :, i])]
    
    return {
        'x': nonzero_x,
        'y': nonzero_y,
        'z': nonzero_z
    }

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="VISTA3D Segmentation Viewer")
    parser.add_argument("--input", type=str, default="C:\\Users\\Albert\\output\\ct\\ct_seg.nii.gz", 
                        help="Input segmentation file (NIfTI format)")
    parser.add_argument("--output_dir", type=str, default=None, 
                        help="Output directory for visualizations (defaults to same directory as input)")
    
    args = parser.parse_args()
    
    # Ensure input file exists
    file_path = Path(args.input)
    if not file_path.exists():
        print(f"Error: Input file not found: {file_path}")
        sys.exit(1)
    
    # Set output directory
    if args.output_dir is None:
        output_dir = file_path.parent
    else:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"Loading segmentation file: {file_path}")
    data, nii_img = load_segmentation(file_path)
    
    print("\n--- Segmentation Information ---")
    print(f"Dimensions: {data.shape}")
    print(f"Data type: {data.dtype}")
    print(f"Value range: [{np.min(data)}, {np.max(data)}]")
    
    print("\n--- NIfTI Header Information ---")
    print(f"Orientation: {nib.aff2axcodes(nii_img.affine)}")
    print(f"Voxel size: {nii_img.header.get_zooms()}")
    
    print("\n--- Segmentation Analysis ---")
    has_data = analyze_segmentation(data)
    
    if has_data:
        # Find non-zero slices
        nonzero_slices = find_nonzero_slices(data)
        if nonzero_slices:
            print("\n--- Non-zero Slice Ranges ---")
            for axis, slices in nonzero_slices.items():
                if slices:
                    print(f"Axis {axis}: from {min(slices)} to {max(slices)} ({len(slices)} slices)")
        
        # Create visualizations
        visualize_segmentation(data, output_dir)
    
    print("\nAnalysis complete.")

if __name__ == "__main__":
    main()
