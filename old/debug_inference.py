#!/usr/bin/env python3
"""
VISTA3D Inference Debugging Script
"""

import os
import sys
import torch
import numpy as np
import nibabel as nib
import logging
from pathlib import Path

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VISTA3D-Debug")

def main():
    # Step 1: Verify CUDA configuration
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA device count: {torch.cuda.device_count()}")
        logger.info(f"Current CUDA device: {torch.cuda.current_device()}")
        logger.info(f"CUDA device name: {torch.cuda.get_device_name()}")
    
    # Step 2: Load VISTA3D components
    try:
        from vista3d.scripts.infer import InferClass, EVERYTHING_PROMPT, IGNORE_PROMPT
        logger.info(f"Successfully imported VISTA3D components")
        logger.info(f"EVERYTHING_PROMPT contains {len(EVERYTHING_PROMPT)} items")
        logger.info(f"IGNORE_PROMPT contains {len(IGNORE_PROMPT)} items")
    except ImportError as e:
        logger.error(f"Failed to import VISTA3D: {e}")
        return
    
    # Step 3: Load and verify input scan
    input_file = "C:\\Users\\Albert\\Totalsegmentator_dataset_v201\\s0031\\ct.nii.gz"
    logger.info(f"Loading input file: {input_file}")
    try:
        input_nifti = nib.load(input_file)
        input_data = input_nifti.get_fdata()
        logger.info(f"Input shape: {input_data.shape}")
        logger.info(f"Input dtype: {input_data.dtype}")
        logger.info(f"Input value range: [{input_data.min()}, {input_data.max()}]")
        logger.info(f"Input affine: \n{input_nifti.affine}")
    except Exception as e:
        logger.error(f"Failed to load input file: {e}")
        return
    
    # Step 4: Load model directly
    model_path = "./vista3d/models/model.pt"
    logger.info(f"Loading model checkpoint: {model_path}")
    try:
        checkpoint = torch.load(model_path, map_location="cpu")
        logger.info(f"Checkpoint loaded successfully")
        logger.info(f"Checkpoint contains {len(checkpoint)} keys")
        
        # Print some key names to verify structure
        key_sample = list(checkpoint.keys())[:5]
        logger.info(f"Sample keys: {key_sample}")
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return
    
    # Step 5: Create InferClass instance
    logger.info("Creating inference object...")
    try:
        config_file = "./vista3d/configs/infer.yaml"
        infer_obj = InferClass(config_file=config_file)
        logger.info("InferClass created successfully")
        
        # Check model structure
        model = infer_obj.model
        logger.info(f"Model type: {type(model).__name__}")
        
        # Try to move model to CUDA
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        logger.info(f"Model moved to {device}")
        
        # Simple test with random tensor
        try:
            # Create a small test tensor (1, channels, 16, 16, 16)
            channels = 1  # Usually medical images have 1 channel
            test_input = torch.randn(1, channels, 16, 16, 16, device=device)
            
            # Set model to evaluation mode
            model.eval()
            
            # Forward pass with torch.no_grad()
            with torch.no_grad():
                logger.info("Running forward pass with test input...")
                # Add required arguments based on model_registry from infer.py
                output = model(test_input)
                
                logger.info(f"Test output shape: {output.shape}")
                logger.info(f"Test output range: [{output.min().item()}, {output.max().item()}]")
                logger.info(f"Test output has non-zeros: {torch.any(output != 0).item()}")
        except Exception as e:
            logger.error(f"Model forward pass failed: {e}")
    except Exception as e:
        logger.error(f"Failed to create InferClass: {e}")
        return
    
    # Step 6: Test infer_everything directly
    try:
        logger.info("Testing infer_everything method directly...")
        logger.info("This may take some time depending on the input size...")
        
        # Create output directory
        output_dir = "C:\\Users\\Albert\\output\\debug"
        os.makedirs(output_dir, exist_ok=True)
        
        # Override output path in infer_obj
        infer_obj.save_transforms.transforms[0].output_dir = output_dir
        
        # Set specific label prompt
        # Use a small subset of labels for testing (e.g., just liver and spleen)
        test_prompt = [1, 3]  # liver and spleen
        
        # Run inference
        try:
            with torch.cuda.amp.autocast(enabled=infer_obj.amp):
                logger.info(f"Running inference with test prompt {test_prompt}...")
                infer_obj.infer_everything(
                    image_file=input_file,
                    label_prompt=test_prompt
                )
            logger.info("Inference completed successfully")
            
            # Check output file
            output_filename = os.path.basename(input_file).replace(".nii.gz", "_seg.nii.gz")
            output_path = os.path.join(output_dir, output_filename)
            
            logger.info(f"Checking output file: {output_path}")
            if os.path.exists(output_path):
                output_nifti = nib.load(output_path)
                output_data = output_nifti.get_fdata()
                logger.info(f"Output shape: {output_data.shape}")
                logger.info(f"Output value range: [{output_data.min()}, {output_data.max()}]")
                logger.info(f"Output non-zero count: {np.count_nonzero(output_data)}")
                
                if np.count_nonzero(output_data) == 0:
                    logger.error("Output still contains all zeros!")
                else:
                    logger.info("Output contains non-zero values - Success!")
            else:
                logger.error(f"Output file not found: {output_path}")
        except Exception as e:
            logger.error(f"infer_everything failed: {e}")
    except Exception as e:
        logger.error(f"Test infer_everything failed: {e}")
    
    logger.info("Debugging complete")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
