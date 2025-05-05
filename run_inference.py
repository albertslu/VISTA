#!/usr/bin/env python3
"""
VISTA3D Inference Script with enhanced memory management and device compatibility
"""

import os
import sys
import time
import argparse
import logging
import gc
import yaml
import torch
import numpy as np
import nibabel as nib
from pathlib import Path
from monai.utils import set_determinism
from monai.transforms import SaveImage

# Add the current directory to the path so we can import vista3d
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vista3d_inference.log")
    ]
)
logger = logging.getLogger("VISTA3D-Inference")

def check_cuda_compatibility():
    """Check if CUDA is available and compatible with PyTorch."""
    logger.info(f"PyTorch version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    logger.info(f"CUDA available: {cuda_available}")
    
    if not cuda_available:
        # Check if CUDA is installed but PyTorch doesn't see it
        cuda_home = os.environ.get('CUDA_HOME') or os.environ.get('CUDA_PATH')
        if cuda_home and os.path.exists(cuda_home):
            logger.warning(f"CUDA is installed at {cuda_home} but PyTorch was installed without CUDA support")
            logger.warning("Consider reinstalling PyTorch with CUDA support:")
            logger.warning("pip uninstall torch")
            logger.warning("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        else:
            logger.warning("CUDA is not installed or not properly configured")
    else:
        # Test CUDA with a small tensor operation
        try:
            device_count = torch.cuda.device_count()
            logger.info(f"Available GPU devices: {device_count}")
            for i in range(device_count):
                logger.info(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            
            # Try a simple CUDA operation
            x = torch.rand(10, 10).cuda()
            y = x + x
            logger.info("CUDA tensor operation successful")
            del x, y
            torch.cuda.empty_cache()
        except Exception as e:
            logger.error(f"CUDA test failed: {str(e)}")
            cuda_available = False
    
    return cuda_available

def get_optimal_device():
    """Get the optimal device for inference based on availability."""
    if torch.cuda.is_available():
        # Try to use CUDA
        try:
            device = torch.device("cuda:0")
            # Test with a small tensor
            test_tensor = torch.zeros(1, device=device)
            del test_tensor
            logger.info("Using CUDA device")
            return device
        except Exception as e:
            logger.warning(f"CUDA device test failed: {str(e)}")
    
    # Try to use MPS (for Mac)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        try:
            device = torch.device("mps")
            test_tensor = torch.zeros(1, device=device)
            del test_tensor
            logger.info("Using MPS device")
            return device
        except Exception as e:
            logger.warning(f"MPS device test failed: {str(e)}")
    
    # Fallback to CPU
    logger.info("Using CPU device")
    return torch.device("cpu")

def clear_memory():
    """Clear memory caches to free up resources."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Memory cache cleared")

def load_config(config_file):
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load config file: {str(e)}")
        raise

def check_model_checkpoint(ckpt_path):
    """Verify that the model checkpoint exists and is valid."""
    if not os.path.exists(ckpt_path):
        logger.error(f"Checkpoint file not found: {ckpt_path}")
        return False
    
    try:
        # Attempt to load checkpoint
        checkpoint = torch.load(ckpt_path, map_location=torch.device('cpu'))
        logger.info(f"Checkpoint file size: {os.path.getsize(ckpt_path) / (1024*1024):.2f} MB")
        logger.info(f"Checkpoint contains {len(checkpoint)} keys")
        return True
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {str(e)}")
        return False

def save_debug_output(data, output_path, filename):
    """Save raw tensor data for debugging purposes."""
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    
    file_path = os.path.join(output_path, filename)
    try:
        np.save(file_path, data.cpu().numpy() if torch.is_tensor(data) else data)
        logger.info(f"Debug data saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save debug data: {str(e)}")

def verify_nifti_output(output_path, filename):
    """Verify that the NIfTI output file is valid and contains data."""
    try:
        import nibabel as nib
    except ImportError:
        logger.warning("Nibabel not installed, skipping NIfTI verification")
        return False
    
    file_path = os.path.join(output_path, filename)
    if not os.path.exists(file_path):
        logger.error(f"Output file not found: {file_path}")
        return False
    
    try:
        nii = nib.load(file_path)
        data = nii.get_fdata()
        nonzero_voxels = np.count_nonzero(data)
        total_voxels = data.size
        percent_nonzero = (nonzero_voxels / total_voxels) * 100 if total_voxels > 0 else 0
        
        logger.info(f"Output file statistics:")
        logger.info(f"  Shape: {data.shape}")
        logger.info(f"  Non-zero voxels: {nonzero_voxels} ({percent_nonzero:.2f}%)")
        logger.info(f"  Value range: [{np.min(data)}, {np.max(data)}]")
        
        if nonzero_voxels == 0:
            logger.error("Output file contains all zeros!")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to verify output file: {str(e)}")
        return False

def run_inference(args):
    """Run VISTA3D inference with the given arguments."""
    try:
        # Initialize inference
        from vista3d.scripts.infer import InferClass
        infer_obj = InferClass(config_file=args.config)
        
        # Run inference based on mode
        if args.point and args.label:
            # Point-based mode
            point = [float(x) for x in args.point.split(",")]
            points = [point]  # Format as [[x,y,z]]
            point_labels = [args.label]
            
            logger.info(f"Running point-based inference at {point} for label {args.label}")
            result = infer_obj.infer(
                image_file=args.input,
                point=points,
                point_label=point_labels,
                save_mask=True
            )
        else:
            # Full segmentation mode
            from vista3d.scripts.infer import EVERYTHING_PROMPT
            logger.info(f"Running full segmentation with {len(EVERYTHING_PROMPT)} labels")
            result = infer_obj.infer(
                image_file=args.input,
                save_mask=True,
                label_prompt=EVERYTHING_PROMPT
            )
        
        # Save output
        if result is not None:
            output_file = os.path.join(args.output, "ct_seg.nii.gz")
            logger.info(f"Saving segmentation to: {output_file}")
            
            # Convert and save as NIfTI
            result_np = result.cpu().numpy().astype(np.float32)
            nifti_img = nib.Nifti1Image(result_np[0], np.eye(4))
            nib.save(nifti_img, output_file)
            
            if os.path.exists(output_file):
                logger.info(f"Segmentation saved successfully")
                logger.info(f"Output size: {os.path.getsize(output_file) / 1024:.2f} KB")
                return True
        
        logger.error("Inference failed to produce valid output")
        return False
        
    except Exception as e:
        logger.error(f"Error during inference: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="VISTA3D Inference Script")
    parser.add_argument("--input", required=True, help="Input CT scan file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--config", default="./vista3d/configs/infer.yaml", help="Config file")
    parser.add_argument("--point", help="Point coordinates (x,y,z)")
    parser.add_argument("--label", type=int, help="Label for point-based segmentation")
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Run inference
    success = run_inference(args)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
