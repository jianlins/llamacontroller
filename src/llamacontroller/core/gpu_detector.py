"""
GPU status detection and monitoring module.

This module provides functionality to detect and monitor NVIDIA GPU status,
including memory usage and process information. It supports both real GPU
detection via nvidia-smi and mock mode for testing.
"""

import os
import subprocess
import re
from typing import List, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass

from ..utils.logging import get_logger
from ..models.gpu import GpuState

logger = get_logger(__name__)

@dataclass
class GpuProcessInfo:
    """Information about a process using GPU."""
    gpu_index: int
    pid: int
    process_name: str
    used_memory: int  # Memory in MiB

@dataclass
class GpuInfo:
    """Basic GPU information."""
    index: int
    memory_used: int  # Memory in MiB
    memory_total: int  # Memory in MiB
    gpu_utilization: int = 0  # GPU utilization percentage

@dataclass
class GpuStatus:
    """Complete GPU status information."""
    index: int
    state: GpuState
    model_name: Optional[str] = None
    process_info: Optional[List[GpuProcessInfo]] = None
    select_enabled: bool = True
    memory_used: int = 0  # Memory in MiB
    memory_total: int = 0  # Memory in MiB
    gpu_utilization: int = 0  # GPU utilization percentage

class GpuDetector:
    """
    GPU detection and status monitoring.
    
    This class provides methods to detect NVIDIA GPUs using nvidia-smi
    and determine their status based on memory usage.
    """
    
    def __init__(self, memory_threshold_mb: int = 30):
        """
        Initialize GPU detector.

        Args:
            memory_threshold_mb: Memory threshold in MB to consider GPU occupied
        """
        self.memory_threshold_mb = memory_threshold_mb
        self._gpu_model_mapping: Dict[Union[int, str], str] = {}

        logger.info(f"GPU Detector initialized: threshold={memory_threshold_mb}MB")
    
    def set_model_mapping(self, gpu_id: Union[int, str], model_name: str) -> None:
        """
        Set model name for a GPU.
        
        Args:
            gpu_id: GPU ID (0, 1, or "0,1" for both)
            model_name: Name of the model loaded on this GPU
        """
        self._gpu_model_mapping[gpu_id] = model_name
        logger.debug(f"Model mapping set: GPU {gpu_id} -> {model_name}")
    
    def remove_model_mapping(self, gpu_id: Union[int, str]) -> None:
        """
        Remove model mapping for a GPU.
        
        Args:
            gpu_id: GPU ID to remove mapping for
        """
        if gpu_id in self._gpu_model_mapping:
            del self._gpu_model_mapping[gpu_id]
            logger.debug(f"Model mapping removed for GPU {gpu_id}")
    
    def clear_model_mapping(self, gpu_id: Union[int, str]) -> None:
        """
        Clear model mapping for a GPU (alias for remove_model_mapping).
        
        Args:
            gpu_id: GPU ID to clear mapping for
        """
        self.remove_model_mapping(gpu_id)
    
    def get_model_for_gpu(self, gpu_id: Union[int, str]) -> Optional[str]:
        """
        Get model name loaded on a GPU.
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            Model name if loaded, None otherwise
        """
        return self._gpu_model_mapping.get(gpu_id)
    
    def _run_nvidia_smi(self) -> str:
        """
        Run nvidia-smi command and get output.

        Returns:
            nvidia-smi output as string

        Raises:
            RuntimeError: If nvidia-smi fails
        """
        # Create a copy of environment variables to ensure subprocess inherits them
        env = os.environ.copy()
        
        # Check if we're in test/mock mode by looking for mock directory
        # This allows tests to work without requiring external PATH setup
        project_root = Path(__file__).parent.parent.parent.parent
        mock_dir = project_root / "tests" / "mock"
        
        import platform
        current_path = env.get('PATH', '')
        
        try:
            print(f"[DEBUG] _run_nvidia_smi called")
            print(f"[DEBUG] Current PATH (first 200 chars): {current_path[:200]}")
            logger.debug(f"Current PATH: {current_path[:200]}...")
            
            # On Windows, use cmd /c to set PATH and run nvidia-smi in the same subprocess
            if platform.system() == "Windows":
                if mock_dir.exists() and (mock_dir / "nvidia-smi.bat").exists():
                    # Set PATH and run nvidia-smi in the same subprocess command
                    # This ensures the PATH change is effective for the nvidia-smi call
                    command = f'set "PATH={mock_dir};%PATH%" && nvidia-smi'
                    print(f"[DEBUG] Mock mode detected, using command: {command}")
                    logger.debug(f"Mock mode: using command with PATH prepend")
                else:
                    command = "nvidia-smi"
                
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                    shell=True  # Required for command chaining with &&
                )
            else:
                # On Linux/Unix, use standard approach
                command = "nvidia-smi"
                result = subprocess.run(
                    [command],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                    env=env
                )
            print(f"[DEBUG] nvidia-smi executed successfully")
            print(f"[DEBUG] nvidia-smi output:\n{result.stdout}")
            logger.debug(f"nvidia-smi executed successfully")
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] nvidia-smi failed: {e}")
            logger.error(f"nvidia-smi failed: {e}")
            raise RuntimeError(f"nvidia-smi command failed: {e}")
        except subprocess.TimeoutExpired:
            print(f"[ERROR] nvidia-smi timeout")
            logger.error("nvidia-smi timeout")
            raise RuntimeError("nvidia-smi command timed out")
        except FileNotFoundError:
            print(f"[ERROR] nvidia-smi not found in PATH")
            print(f"[ERROR] PATH was: {current_path[:200]}")
            logger.error(f"nvidia-smi not found. PATH: {current_path[:200]}")
            raise RuntimeError("nvidia-smi not found. NVIDIA drivers may not be installed.")
    
    def parse_gpu_info(self, nvidia_smi_output: str) -> List[GpuInfo]:
        """
        Parse GPU information from nvidia-smi output.
        
        Args:
            nvidia_smi_output: Output from nvidia-smi command
            
        Returns:
            List of GpuInfo objects
        """
        gpu_list = []
        
        # Parse the table section with GPU information
        # Look for lines like: |   0  NVIDIA A40                   TCC   | ...
        # Then parse memory from: |  0%   24C    P8              11W / 300W |      1MiB / 46068MiB |
        
        lines = nvidia_smi_output.split('\n')
        current_gpu = None
        
        for i, line in enumerate(lines):
            # Match GPU index line
            gpu_match = re.match(r'\|\s+(\d+)\s+(.+?)\s+(TCC|WDDM)', line)
            if gpu_match:
                current_gpu = int(gpu_match.group(1))
            
            # Match memory line (appears after GPU index line)
            if current_gpu is not None:
                memory_match = re.search(r'(\d+)MiB\s*/\s*(\d+)MiB', line)
                if memory_match:
                    memory_used = int(memory_match.group(1))
                    memory_total = int(memory_match.group(2))
                    
                    # Extract GPU utilization - appears after memory section as "X%" before "Default"
                    # Format: |  0%   24C    P8   11W / 300W |      1MiB / 46068MiB |      30%      Default |
                    # We need to find the percentage AFTER the memory section (third column)
                    gpu_util = 0
                    # Look for pattern: MiB | followed by spaces and a percentage
                    util_match = re.search(r'MiB\s*\|\s*(\d+)%\s+\w+', line)
                    if util_match:
                        gpu_util = int(util_match.group(1))
                    
                    gpu_list.append(GpuInfo(
                        index=current_gpu,
                        memory_used=memory_used,
                        memory_total=memory_total,
                        gpu_utilization=gpu_util
                    ))
                    
                    logger.debug(
                        f"Parsed GPU {current_gpu}: "
                        f"{memory_used}MiB / {memory_total}MiB, "
                        f"GPU-Util: {gpu_util}%"
                    )
                    
                    current_gpu = None  # Reset for next GPU
        
        return gpu_list
    
    def parse_gpu_processes(self, nvidia_smi_output: str) -> List[GpuProcessInfo]:
        """
        Parse GPU process information from nvidia-smi output.
        
        Args:
            nvidia_smi_output: Output from nvidia-smi command
            
        Returns:
            List of GpuProcessInfo objects
        """
        process_list = []
        
        # Look for process table section
        # Format: |  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
        #         |        ID   ID                                                             Usage      |
        #         |  0      -    -      12345      C   python.exe                                  256MiB |
        
        in_process_section = False
        lines = nvidia_smi_output.split('\n')
        
        for line in lines:
            if 'Processes:' in line:
                in_process_section = True
                continue
            
            if not in_process_section:
                continue
            
            # Match process line
            # Format: |  0      -    -      12345      C   python.exe                                  256MiB |
            process_match = re.match(
                r'\|\s+(\d+)\s+[\-\d]+\s+[\-\d]+\s+(\d+)\s+\w+\s+(.+?)\s+(\d+)MiB',
                line
            )
            
            if process_match:
                gpu_index = int(process_match.group(1))
                pid = int(process_match.group(2))
                process_name = process_match.group(3).strip()
                used_memory = int(process_match.group(4))
                
                process_list.append(GpuProcessInfo(
                    gpu_index=gpu_index,
                    pid=pid,
                    process_name=process_name,
                    used_memory=used_memory
                ))
                
                logger.debug(
                    f"Parsed process: GPU {gpu_index}, PID {pid}, "
                    f"{process_name}, {used_memory}MiB"
                )
        
        return process_list
    
    def detect_gpus(self) -> List[GpuStatus]:
        """
        Detect GPUs and determine their status.
        
        Returns:
            List of GpuStatus objects, or list with CPU fallback if no GPUs
        """
        print(f"[DEBUG] detect_gpus() called", flush=True)
        try:
            # Get nvidia-smi output
            print(f"[DEBUG] Calling _run_nvidia_smi()...", flush=True)
            nvidia_smi_output = self._run_nvidia_smi()
            print(f'[DEBUG] Got nvidia_smi_output (length: {len(nvidia_smi_output)} chars)', flush=True)
            
            # Parse GPU info and processes
            gpu_info_list = self.parse_gpu_info(nvidia_smi_output)
            process_info_list = self.parse_gpu_processes(nvidia_smi_output)
            
            if not gpu_info_list:
                logger.warning("No GPUs detected, falling back to CPU")
                return self._get_cpu_fallback()
            
            # Build status for each GPU
            gpu_status_list = []
            
            for gpu in gpu_info_list:
                # Check if memory usage exceeds threshold
                if gpu.memory_used > self.memory_threshold_mb:
                    # Get model name if we know about it
                    model_name = self.get_model_for_gpu(gpu.index)
                    
                    if model_name:
                        # Model loaded by controller
                        status = GpuStatus(
                            index=gpu.index,
                            state=GpuState.MODEL_LOADED,
                            model_name=model_name,
                            select_enabled=True,
                            memory_used=gpu.memory_used,
                            memory_total=gpu.memory_total,
                            gpu_utilization=gpu.gpu_utilization
                        )
                    else:
                        # Occupied by others
                        # Get process info for this GPU
                        gpu_processes = [
                            p for p in process_info_list 
                            if p.gpu_index == gpu.index
                        ]
                        
                        status = GpuStatus(
                            index=gpu.index,
                            state=GpuState.OCCUPIED_BY_OTHERS,
                            model_name="Occupied by someone else",
                            process_info=gpu_processes if gpu_processes else None,
                            select_enabled=False,
                            memory_used=gpu.memory_used,
                            memory_total=gpu.memory_total,
                            gpu_utilization=gpu.gpu_utilization
                        )
                else:
                    # GPU is idle (memory usage below threshold)
                    # Still check for model mapping in case model was loaded but memory dropped
                    model_name = self.get_model_for_gpu(gpu.index)
                    
                    status = GpuStatus(
                        index=gpu.index,
                        state=GpuState.IDLE,
                        model_name=model_name,
                        select_enabled=True,
                        memory_used=gpu.memory_used,
                        memory_total=gpu.memory_total,
                        gpu_utilization=gpu.gpu_utilization
                    )
                
                gpu_status_list.append(status)
                
                logger.debug(
                    f"GPU {gpu.index} status: {status.state.value}, "
                    f"memory: {status.memory_used}/{status.memory_total}MiB"
                )
            
            return gpu_status_list
            
        except RuntimeError as e:
            logger.warning(f"GPU detection failed: {e}, falling back to CPU")
            return self._get_cpu_fallback()
        except Exception as e:
            logger.error(f"Unexpected error in GPU detection: {e}", exc_info=True)
            return self._get_cpu_fallback()
    
    def _get_cpu_fallback(self) -> List[GpuStatus]:
        """
        Get CPU fallback status.
        
        Returns:
            List with single CPU status
        """
        return [
            GpuStatus(
                index=-1,  # Use -1 to indicate CPU
                state=GpuState.IDLE,
                model_name=None,
                select_enabled=True,
                memory_used=0,
                memory_total=0
            )
        ]
    
    def get_gpu_count(self) -> int:
        """
        Get number of available GPUs.
        
        Returns:
            Number of GPUs, or 0 if none available
        """
        try:
            statuses = self.detect_gpus()
            # Filter out CPU fallback (index -1)
            gpu_count = len([s for s in statuses if s.index >= 0])
            return gpu_count
        except Exception as e:
            logger.error(f"Failed to get GPU count: {e}")
            return 0
