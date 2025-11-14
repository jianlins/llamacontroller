"""
Test script to verify GPU detection with all mock scenarios.

This script tests the GpuDetector with different nvidia-smi output scenarios
to ensure it correctly parses and classifies GPU states.
"""

from pathlib import Path
from llamacontroller.core.gpu_detector import GpuDetector
from llamacontroller.models.gpu import GpuState


def test_scenario(scenario_name: str, scenario_file: str):
    """Test a specific scenario."""
    print(f"\n{'='*70}")
    print(f"Testing scenario: {scenario_name}")
    print('='*70)
    
    detector = GpuDetector(
        memory_threshold_mb=30,
        mock_mode=True,
        mock_data_path=scenario_file
    )
    
    try:
        statuses = detector.detect_gpus()
        
        print(f"\nDetected {len(statuses)} GPU(s):\n")
        
        for status in statuses:
            print(f"GPU {status.index}:")
            print(f"  State: {status.state.value}")
            print(f"  Memory: {status.memory_used}/{status.memory_total} MiB")
            print(f"  Selectable: {'Yes' if status.select_enabled else 'No'}")
            
            if status.model_name:
                print(f"  Model: {status.model_name}")
            
            if status.process_info:
                print(f"  Processes:")
                for proc in status.process_info:
                    print(f"    - PID {proc.pid}: {proc.process_name} ({proc.used_memory} MiB)")
            
            print()
        
        return True, statuses
        
    except Exception as e:
        print(f"\n❌ Error testing scenario: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def verify_scenario(scenario_name: str, statuses, expected_results: dict):
    """Verify scenario results match expectations."""
    print(f"Verifying {scenario_name}...")
    
    if not statuses:
        print("  ❌ No statuses returned")
        return False
    
    all_passed = True
    
    for gpu_idx, expected in expected_results.items():
        matching = [s for s in statuses if s.index == gpu_idx]
        
        if not matching:
            print(f"  ❌ GPU {gpu_idx}: Not found in results")
            all_passed = False
            continue
        
        status = matching[0]
        
        # Check state
        if status.state != expected['state']:
            print(f"  ❌ GPU {gpu_idx}: Expected state {expected['state'].value}, "
                  f"got {status.state.value}")
            all_passed = False
        
        # Check selectable
        if status.select_enabled != expected['selectable']:
            print(f"  ❌ GPU {gpu_idx}: Expected selectable={expected['selectable']}, "
                  f"got {status.select_enabled}")
            all_passed = False
        
        # Check memory threshold behavior
        if 'memory_above_threshold' in expected:
            above = status.memory_used > 30
            if above != expected['memory_above_threshold']:
                print(f"  ❌ GPU {gpu_idx}: Memory usage {status.memory_used}MiB "
                      f"doesn't match threshold expectation")
                all_passed = False
    
    if all_passed:
        print(f"  ✅ All checks passed for {scenario_name}")
    
    return all_passed


def main():
    """Run all scenario tests."""
    base_path = Path("tests/mock/scenarios")
    
    scenarios = [
        {
            'name': 'All GPUs Idle',
            'file': base_path / 'all_idle.txt',
            'expected': {
                0: {'state': GpuState.IDLE, 'selectable': True, 'memory_above_threshold': False},
                1: {'state': GpuState.IDLE, 'selectable': True, 'memory_above_threshold': False}
            }
        },
        {
            'name': 'All GPUs Occupied',
            'file': base_path / 'all_occupied.txt',
            'expected': {
                0: {'state': GpuState.OCCUPIED_BY_OTHERS, 'selectable': False, 'memory_above_threshold': True},
                1: {'state': GpuState.OCCUPIED_BY_OTHERS, 'selectable': False, 'memory_above_threshold': True}
            }
        },
        {
            'name': 'Mixed Status',
            'file': base_path / 'mixed_status.txt',
            'expected': {
                0: {'state': GpuState.IDLE, 'selectable': True, 'memory_above_threshold': False},
                1: {'state': GpuState.OCCUPIED_BY_OTHERS, 'selectable': False, 'memory_above_threshold': True}
            }
        },
        {
            'name': 'Single GPU',
            'file': base_path / 'single_gpu.txt',
            'expected': {
                0: {'state': GpuState.OCCUPIED_BY_OTHERS, 'selectable': False, 'memory_above_threshold': True}
            }
        }
    ]
    
    print("\n" + "="*70)
    print("GPU DETECTION MOCK TEST SUITE")
    print("="*70)
    
    results = []
    
    for scenario in scenarios:
        success, statuses = test_scenario(scenario['name'], str(scenario['file']))
        
        if success:
            verified = verify_scenario(scenario['name'], statuses, scenario['expected'])
            results.append((scenario['name'], verified))
        else:
            results.append((scenario['name'], False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} scenarios passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
