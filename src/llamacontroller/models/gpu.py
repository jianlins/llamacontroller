"""
Pydantic models for GPU status API responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class GpuState(str, Enum):
    """GPU state enumeration."""
    IDLE = "idle"
    MODEL_LOADED = "model_loaded"
    OCCUPIED_BY_OTHERS = "occupied_by_others"

class GpuProcessInfoResponse(BaseModel):
    """GPU process information response."""
    
    gpu_index: int = Field(..., description="GPU index")
    pid: int = Field(..., description="Process ID")
    process_name: str = Field(..., description="Process name")
    used_memory: int = Field(..., description="Used memory in MiB")
    user_id: Optional[str] = Field(None, description="User ID running the process")

class GpuStatusResponse(BaseModel):
    """Single GPU status response."""

    class Config:
        protected_namespaces = ()
    
    index: int = Field(..., description="GPU index (-1 for CPU)")
    state: GpuState = Field(..., description="GPU state")
    model_name: Optional[str] = Field(None, description="Name of loaded model (if any)")
    process_info: Optional[List[GpuProcessInfoResponse]] = Field(None, description="Process information")
    select_enabled: bool = Field(..., description="Whether GPU can be selected for loading models")
    memory_used: int = Field(..., description="Used memory in MiB")
    memory_total: int = Field(..., description="Total memory in MiB")
    gpu_utilization: int = Field(0, description="GPU utilization percentage (Volatile)")

class AllGpuStatusResponse(BaseModel):
    """Response containing status of all GPUs."""

    gpus: List[GpuStatusResponse] = Field(..., description="List of GPU statuses")
    gpu_count: int = Field(..., description="Number of GPUs detected")
    detection_enabled: bool = Field(..., description="Whether GPU detection is enabled")

class GpuDetectionConfigResponse(BaseModel):
    """GPU detection configuration response."""

    enabled: bool = Field(..., description="Whether GPU detection is enabled")
    memory_threshold_mb: int = Field(..., description="Memory threshold in MB")
