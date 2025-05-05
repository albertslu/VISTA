#!/usr/bin/env python
# CUDA diagnostic script for VISTA3D

import os
import sys
import torch
import platform

def check_cuda_configuration():
    """Check CUDA configuration and print detailed information"""
    print("\n===== CUDA Configuration Diagnostic =====")
    print(f"Python version: {platform.python_version()}")
    print(f"PyTorch version: {torch.__version__}")
    print(f"System: {platform.system()} {platform.release()}")
    
    # Check CUDA availability
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU device count: {torch.cuda.device_count()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")
        print(f"Device capability: {torch.cuda.get_device_capability(0)}")
        
        # Check memory
        print("\n----- GPU Memory Information -----")
        print(f"Total memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        print(f"Allocated memory: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
        print(f"Reserved memory: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")
        
        # Test tensor creation on GPU
        try:
            print("\n----- GPU Tensor Test -----")
            x = torch.rand(1000, 1000).cuda()
            y = torch.rand(1000, 1000).cuda()
            z = x @ y  # Matrix multiplication to test computation
            print(f"GPU tensor test successful. Result shape: {z.shape}")
            del x, y, z
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"GPU tensor test failed: {e}")
    
    # Check environment variables
    print("\n----- CUDA Environment Variables -----")
    cuda_env_vars = [
        "CUDA_HOME", "CUDA_PATH", "CUDA_VISIBLE_DEVICES", 
        "LD_LIBRARY_PATH", "PATH"
    ]
    for var in cuda_env_vars:
        print(f"{var}: {os.environ.get(var, 'Not set')}")
    
    # Check PyTorch build information
    print("\n----- PyTorch Build Information -----")
    print(f"Debug build: {torch.version.debug}")
    print(f"Has CUDA: {torch.cuda.is_available()}")
    print(f"CUDNN Version: {torch.backends.cudnn.version() if torch.cuda.is_available() else 'N/A'}")
    print(f"CUDNN Enabled: {torch.backends.cudnn.enabled if torch.cuda.is_available() else 'N/A'}")
    
    # Check if PyTorch can see the GPU
    if cuda_available:
        try:
            print("\n----- PyTorch Device Compatibility Test -----")
            # Try different device specifications
            devices = ["cuda", "cuda:0", torch.device("cuda")]
            for device_spec in devices:
                try:
                    device = torch.device(device_spec)
                    test_tensor = torch.zeros(10, device=device)
                    print(f"Successfully created tensor on {device_spec}")
                except Exception as e:
                    print(f"Failed to create tensor on {device_spec}: {e}")
        except Exception as e:
            print(f"Device compatibility test failed: {e}")
    
    print("\n===== End of Diagnostic =====")

if __name__ == "__main__":
    check_cuda_configuration()
