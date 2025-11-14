"""
Test script for GPU detection functionality.

This script tests the GPU detection module with mock data.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llamacontroller.core.gpu_detector import GpuDetector
from llamacontroller.models.gpu import GpuState


def test_parser():
    """Test nvidia-smi output parsing."""
    print("=" * 60)
    print("Testing GPU Detection Parser")
    print("=" * 60)
    
    # Initialize detector in mock mode
    detector = GpuDetector(
        memory_threshold_mb=30,
        mock_mode=True,
        mock_data_path="data/gpu.txt"
    )
    
    print(f"\nDetector initialized:")
    print(f"  Memory threshold: {detector.memory_threshold_mb}MB")
    print(f"  Mock mode: {detector.mock_mode}")
    print(f"  Mock data path: {detector.mock_data_path}")
    
    # Detect GPUs
    print("\n" + "-" * 60)
    print("Detecting GPUs...")
    print("-" * 60)
    
    gpu_statuses = detector.detect_gpus()
    
    print(f"\nDetected {len(gpu_statuses)} GPU(s):\n")
    
    for status in gpu_statuses:
        print(f"GPU {status.index}:")
        print(f"  State: {status.state.value}")
        print(f"  Memory: {status.memory_used}MiB / {status.memory_total}MiB")
        print(f"  Selectable: {status.select_enabled}")
        
        if status.model_name:
            print(f"  Model: {status.model_name}")
        
        if status.process_info:
            print(f"  Processes:")
            for proc in status.process_info:
                print(f"    - PID {proc.pid}: {proc.process_name} ({proc.used_memory}MiB)")
        
        print()
    
    # Test model mapping
    print("-" * 60)
    print("Testing model mapping...")
    print("-" * 60)
    
    detector.set_model_mapping(0, "Test Model on GPU 0")
    detector.set_model_mapping(1, "Test Model on GPU 1")
    
    gpu_statuses = detector.detect_gpus()
    
    print("\nAfter setting model mappings:\n")
    for status in gpu_statuses:
        if status.index >= 0:
            print(f"GPU {status.index}:")
            print(f"  State: {status.state.value}")
            print(f"  Model: {status.model_name}")
            print()
    
    # Verify behavior
    print("-" * 60)
    print("Verification")
    print("-" * 60)
    
    # GPU 0: 1MiB < 30MB threshold, should be IDLE even with model mapping
    gpu0 = [g for g in gpu_statuses if g.index == 0][0]
    assert gpu0.state == GpuState.IDLE, f"GPU 0 should be IDLE (1MiB < 30MB), got {gpu0.state}"
    assert gpu0.model_name == "Test Model on GPU 0", "Model mapping should still be stored"
    assert gpu0.select_enabled == True, "IDLE GPU should be selectable"
    print("✓ GPU 0: Correctly shows as IDLE (memory below threshold)")
    
    # GPU 1: 363MiB > 30MB threshold with model mapping, should be MODEL_LOADED
    gpu1 = [g for g in gpu_statuses if g.index == 1][0]
    assert gpu1.state == GpuState.MODEL_LOADED, f"GPU 1 should be MODEL_LOADED (363MiB > 30MB), got {gpu1.state}"
    assert gpu1.model_name == "Test Model on GPU 1"
    assert gpu1.select_enabled == True, "MODEL_LOADED GPU should be selectable"
    print("✓ GPU 1: Correctly shows as MODEL_LOADED (memory over threshold with mapping)")
    
    # Test OCCUPIED_BY_OTHERS state
    print("\n" + "-" * 60)
    print("Testing OCCUPIED_BY_OTHERS state...")
    print("-" * 60)
    
    # Clear GPU 1 mapping to test OCCUPIED_BY_OTHERS
    detector.clear_model_mapping(1)
    gpu_statuses = detector.detect_gpus()
    
    gpu1_no_mapping = [g for g in gpu_statuses if g.index == 1][0]
    assert gpu1_no_mapping.state == GpuState.OCCUPIED_BY_OTHERS, \
        f"GPU 1 should be OCCUPIED_BY_OTHERS without mapping, got {gpu1_no_mapping.state}"
    assert gpu1_no_mapping.model_name == "Occupied by someone else"
    assert gpu1_no_mapping.select_enabled == False, "Occupied GPU should not be selectable"
    print("✓ GPU 1: Correctly shows as OCCUPIED_BY_OTHERS without model mapping")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_parser()
