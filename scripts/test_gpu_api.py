"""
Test script for GPU API endpoints.

This script tests the GPU status API endpoints.
"""

import sys
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"  # Default password

def test_gpu_api():
    """Test GPU API endpoints."""
    print("=" * 60)
    print("Testing GPU API Endpoints")
    print("=" * 60)
    
    # Step 1: Login to get session
    print("\n1. Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        return False
    
    session_id = login_response.json()["session_id"]
    print(f"✓ Logged in successfully (session: {session_id[:8]}...)")
    
    # Prepare headers with session cookie
    headers = {
        "Cookie": f"session_id={session_id}"
    }
    
    # Step 2: Test GPU status endpoint
    print("\n2. Testing GPU status endpoint...")
    status_response = requests.get(
        f"{BASE_URL}/gpu/status",
        headers=headers
    )
    
    if status_response.status_code != 200:
        print(f"❌ GPU status failed: {status_response.status_code}")
        print(f"   Response: {status_response.text}")
        return False
    
    status_data = status_response.json()
    print(f"✓ GPU status retrieved successfully")
    print(f"   Found {len(status_data['gpus'])} GPU(s)")
    
    for gpu in status_data['gpus']:
        print(f"\n   GPU {gpu['index']}:")
        print(f"     State: {gpu['state']}")
        print(f"     Memory: {gpu['memory_used']}MiB / {gpu['memory_total']}MiB")
        print(f"     Selectable: {gpu['select_enabled']}")
        if gpu['model_name']:
            print(f"     Model: {gpu['model_name']}")
        if gpu['process_info']:
            print(f"     Processes:")
            for proc in gpu['process_info']:
                print(f"       - PID {proc['pid']}: {proc['process_name']} ({proc['used_memory']}MiB)")
    
    # Step 3: Test GPU count endpoint
    print("\n3. Testing GPU count endpoint...")
    count_response = requests.get(
        f"{BASE_URL}/gpu/count",
        headers=headers
    )
    
    if count_response.status_code != 200:
        print(f"❌ GPU count failed: {count_response.status_code}")
        print(f"   Response: {count_response.text}")
        return False
    
    count_data = count_response.json()
    print(f"✓ GPU count retrieved: {count_data['count']} GPU(s)")
    
    # Step 4: Test GPU detection config endpoint
    print("\n4. Testing GPU detection config endpoint...")
    config_response = requests.get(
        f"{BASE_URL}/gpu/config",
        headers=headers
    )
    
    if config_response.status_code != 200:
        print(f"❌ GPU config failed: {config_response.status_code}")
        print(f"   Response: {config_response.text}")
        return False
    
    config_data = config_response.json()
    print(f"✓ GPU detection config retrieved")
    print(f"   Enabled: {config_data['enabled']}")
    print(f"   Memory threshold: {config_data['memory_threshold_mb']}MB")
    print(f"   Mock mode: {config_data['mock_mode']}")
    print(f"   GPU count: {config_data['gpu_count']}")
    print(f"   Detection available: {config_data['detection_available']}")
    
    # Step 5: Verify data consistency
    print("\n5. Verifying data consistency...")
    if len(status_data['gpus']) != count_data['count']:
        print(f"❌ Inconsistent GPU count: status={len(status_data['gpus'])}, count={count_data['count']}")
        return False
    
    if config_data['gpu_count'] != count_data['count']:
        print(f"❌ Inconsistent GPU count: config={config_data['gpu_count']}, count={count_data['count']}")
        return False
    
    print("✓ Data consistency verified")
    
    print("\n" + "=" * 60)
    print("All GPU API tests passed! ✓")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_gpu_api()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n❌ Failed to connect to server")
        print("   Make sure the server is running at http://localhost:3000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
