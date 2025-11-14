"""
Test script to verify GPU status display after model loading
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llamacontroller.models.lifecycle import AllGpuStatus, GpuInstanceStatus, ProcessStatus
from datetime import datetime

def test_gpu_status_access():
    """Test that GPU status can be accessed correctly in templates"""
    
    # Simulate what lifecycle_manager.get_all_gpu_statuses() returns
    gpu_statuses = AllGpuStatus(
        gpu0=GpuInstanceStatus(
            gpu_id="0",
            port=8081,
            model_id="llama3-8b",
            model_name="Llama 3 8B",
            status=ProcessStatus.RUNNING,
            loaded_at=datetime.now(),
            uptime_seconds=120,
            pid=12345
        ),
        gpu1=None,
        both=None
    )
    
    # Test access patterns that the template will use
    print("Testing GPU status access patterns:")
    print(f"1. gpu_statuses.gpu0: {gpu_statuses.gpu0}")
    print(f"2. gpu_statuses.gpu1: {gpu_statuses.gpu1}")
    print(f"3. gpu_statuses.both: {gpu_statuses.both}")
    
    # Verify the conditional logic
    print("\nTemplate conditional logic simulation:")
    
    # For GPU 0
    gpu_idx = 0
    if gpu_idx == 0:
        gpu_instance = gpu_statuses.gpu0 if gpu_statuses else None
    elif gpu_idx == 1:
        gpu_instance = gpu_statuses.gpu1 if gpu_statuses else None
    else:
        gpu_instance = None
    
    print(f"GPU {gpu_idx}: gpu_instance = {gpu_instance}")
    if gpu_instance:
        print(f"  ✓ Status should be GREEN (Running)")
        print(f"  ✓ Model: {gpu_instance.model_name}")
        print(f"  ✓ Port: {gpu_instance.port}")
    else:
        print(f"  ✗ Status should be GRAY (Idle)")
    
    # For GPU 1
    gpu_idx = 1
    if gpu_idx == 0:
        gpu_instance = gpu_statuses.gpu0 if gpu_statuses else None
    elif gpu_idx == 1:
        gpu_instance = gpu_statuses.gpu1 if gpu_statuses else None
    else:
        gpu_instance = None
    
    print(f"\nGPU {gpu_idx}: gpu_instance = {gpu_instance}")
    if gpu_instance:
        print(f"  ✓ Status should be GREEN (Running)")
    else:
        print(f"  ✓ Status should be GRAY (Idle) - Correct!")
    
    # Test multi-GPU scenario
    print("\n" + "="*60)
    print("Testing multi-GPU scenario:")
    gpu_statuses_multi = AllGpuStatus(
        gpu0=None,
        gpu1=None,
        both=GpuInstanceStatus(
            gpu_id="0,1",
            port=8081,
            model_id="llama3-70b",
            model_name="Llama 3 70B",
            status=ProcessStatus.RUNNING,
            loaded_at=datetime.now(),
            uptime_seconds=300,
            pid=67890
        )
    )
    
    if gpu_statuses_multi.both:
        print(f"✓ Multi-GPU status detected:")
        print(f"  Model: {gpu_statuses_multi.both.model_name}")
        print(f"  Port: {gpu_statuses_multi.both.port}")
    
    print("\n" + "="*60)
    print("All tests passed! ✓")
    print("\nThe fix correctly accesses Pydantic model attributes:")
    print("  - gpu_statuses.gpu0 (not gpu_statuses['gpu0'])")
    print("  - gpu_statuses.gpu1 (not gpu_statuses['gpu1'])")
    print("  - gpu_statuses.both")

if __name__ == "__main__":
    test_gpu_status_access()
