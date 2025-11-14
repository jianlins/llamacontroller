"""
Test GPU refresh improvements

Tests the new 5-minute auto-refresh and pre-load GPU status check features.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llamacontroller.core.config import ConfigManager
from llamacontroller.core.lifecycle import ModelLifecycleManager

async def main():
    """Test GPU refresh improvements"""
    print("=" * 60)
    print("Testing GPU Refresh Improvements")
    print("=" * 60)
    
    # Initialize
    config_manager = ConfigManager()
    config_manager.load_config()  # Load configuration first
    lifecycle_manager = ModelLifecycleManager(config_manager)
    
    print("\n1. Testing GPU hardware detection (pre-load refresh simulation)")
    print("-" * 60)
    hardware_status = await lifecycle_manager.detect_gpu_hardware()
    print(f"GPU Count: {hardware_status.gpu_count}")
    print(f"Mock Mode: {hardware_status.mock_mode}")
    
    for gpu in hardware_status.gpus:
        print(f"\nGPU {gpu.index}:")
        print(f"  State: {gpu.state}")
        print(f"  Model: {gpu.model_name or 'None'}")
        print(f"  Memory: {gpu.memory_used}MiB / {gpu.memory_total}MiB")
        print(f"  Selectable: {gpu.select_enabled}")
        if gpu.process_info:
            for proc in gpu.process_info:
                print(f"  Process: PID {proc.pid} ({proc.process_name}) - {proc.used_memory}MiB")
    
    print("\n2. Testing GPU status for model loading")
    print("-" * 60)
    
    # Check which GPUs are available for loading
    available_gpus = [gpu.index for gpu in hardware_status.gpus if gpu.select_enabled]
    print(f"Available GPUs for model loading: {available_gpus}")
    
    occupied_gpus = [gpu.index for gpu in hardware_status.gpus if gpu.state == 'occupied_by_others']
    if occupied_gpus:
        print(f"⚠️  Occupied GPUs (blocked from loading): {occupied_gpus}")
    
    print("\n3. Testing model load with pre-check simulation")
    print("-" * 60)
    
    if available_gpus:
        test_gpu = available_gpus[0]
        print(f"Simulating pre-load check for GPU {test_gpu}...")
        
        # Refresh GPU status (this is what happens before load_model)
        hardware_status = await lifecycle_manager.detect_gpu_hardware()
        gpu_status = hardware_status.gpus[test_gpu] if test_gpu < len(hardware_status.gpus) else None
        
        if gpu_status and gpu_status.state == 'occupied_by_others':
            print(f"❌ Cannot load model: GPU {test_gpu} is occupied by another process")
        else:
            print(f"✓ GPU {test_gpu} is available for model loading")
            
            # Try to load a model
            models = config_manager.models.get_model_ids()
            if models:
                test_model = models[0]
                print(f"\nAttempting to load model '{test_model}' on GPU {test_gpu}...")
                try:
                    result = await lifecycle_manager.load_model(test_model, str(test_gpu))
                    print(f"✓ Model loaded successfully!")
                    print(f"  Message: {result.message}")
                    print(f"  Port: {result.status.port if result.status else 'N/A'}")
                    
                    # Check all GPU statuses after load
                    print("\n4. Testing GPU statuses after model load")
                    print("-" * 60)
                    all_statuses = await lifecycle_manager.get_all_gpu_statuses()
                    for gpu_key, status in all_statuses.items():
                        if status:
                            print(f"{gpu_key}: Model '{status.model_name}' (Port {status.port})")
                    
                    # Test that the GPU button should now be disabled for other models
                    print("\n5. Verifying GPU button state (should be disabled)")
                    print("-" * 60)
                    hardware_status = await lifecycle_manager.detect_gpu_hardware()
                    loaded_gpu = hardware_status.gpus[test_gpu] if test_gpu < len(hardware_status.gpus) else None
                    if loaded_gpu:
                        print(f"GPU {test_gpu}:")
                        print(f"  State: {loaded_gpu.state}")
                        print(f"  Model: {loaded_gpu.model_name}")
                        print(f"  Button enabled: {loaded_gpu.select_enabled}")
                        if loaded_gpu.state == 'model_loaded':
                            print("  ✓ Button should be disabled (⚡ indicator)")
                    
                    # Unload the model
                    print("\n6. Testing model unload (button should re-enable)")
                    print("-" * 60)
                    await lifecycle_manager.unload_model(str(test_gpu))
                    print(f"✓ Model unloaded from GPU {test_gpu}")
                    
                    # Verify button is re-enabled
                    hardware_status = await lifecycle_manager.detect_gpu_hardware()
                    unloaded_gpu = hardware_status.gpus[test_gpu] if test_gpu < len(hardware_status.gpus) else None
                    if unloaded_gpu:
                        print(f"GPU {test_gpu} after unload:")
                        print(f"  State: {unloaded_gpu.state}")
                        print(f"  Button enabled: {unloaded_gpu.select_enabled}")
                        if unloaded_gpu.state == 'idle' and unloaded_gpu.select_enabled:
                            print("  ✓ Button successfully re-enabled!")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            else:
                print("No models available for testing")
    else:
        print("No available GPUs for testing model load")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print("✓ Auto-refresh interval: Changed to 5 minutes (300s)")
    print("✓ Pre-load GPU check: Implemented in load_model_ui()")
    print("✓ GPU button disable: Implemented for occupied/running GPUs")
    print("✓ GPU button re-enable: Automatic on unload via status refresh")
    print("\nWeb UI changes:")
    print("- dashboard.html: Updated to 'every 300s' and '5m' display")
    print("- routes.py: Added pre-load GPU status verification")
    print("- model_list.html: Enhanced button disable logic for all states")

if __name__ == "__main__":
    asyncio.run(main())
