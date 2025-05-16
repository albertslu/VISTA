#!/usr/bin/env python3
"""
Test script to check if a NIfTI file can be loaded with nibabel
"""

import os
import sys
import nibabel as nib

def test_nifti_file(file_path):
    """Test if a NIfTI file can be loaded with nibabel."""
    print(f"Testing file: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    print(f"File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
    
    try:
        img = nib.load(file_path)
        print("File loaded successfully!")
        print(f"Image shape: {img.shape}")
        print(f"Data type: {img.get_data_dtype()}")
        print(f"Affine: \n{img.affine}")
        return True
    except Exception as e:
        print(f"Error loading file: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_nifti.py <path_to_nifti_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = test_nifti_file(file_path)
    sys.exit(0 if success else 1)
