"""
GPU status API endpoints.

This module provides REST API endpoints for GPU status detection and monitoring.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_user
from ..api.dependencies import get_lifecycle_manager
from ..models.gpu import (
    GpuStatusResponse,
    AllGpuStatusResponse,
    GpuDetectionConfigResponse,
    GpuProcessInfoResponse
)
from ..db.models import User
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/gpu", tags=["gpu"])


def _convert_process_info(process_info) -> GpuProcessInfoResponse:
    """Convert GpuProcessInfo to response model."""
    return GpuProcessInfoResponse(
        gpu_index=process_info.gpu_index,
        pid=process_info.pid,
        process_name=process_info.process_name,
        used_memory=process_info.used_memory
    )


def _convert_gpu_status(status) -> GpuStatusResponse:
    """Convert GpuStatus to response model."""
    process_info = None
    if status.process_info:
        process_info = [_convert_process_info(p) for p in status.process_info]
    
    return GpuStatusResponse(
        index=status.index,
        state=status.state,
        model_name=status.model_name,
        process_info=process_info,
        select_enabled=status.select_enabled,
        memory_used=status.memory_used,
        memory_total=status.memory_total
    )


@router.get("/status", response_model=AllGpuStatusResponse)
async def get_gpu_status(
    current_user: User = Depends(get_current_user)
) -> AllGpuStatusResponse:
    """
    Get current GPU status for all available GPUs.
    
    Returns GPU information including:
    - GPU index
    - Current state (idle, model_loaded, occupied_by_others)
    - Model name (if loaded by controller)
    - Memory usage
    - Process information (if occupied by others)
    
    Requires authentication.
    """
    try:
        lifecycle = get_lifecycle_manager()
        
        # Get GPU status from detector
        response = await lifecycle.detect_gpu_hardware()
        
        logger.info(f"GPU status retrieved by user {current_user.username}")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get GPU status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve GPU status: {str(e)}"
        )


@router.get("/config", response_model=GpuDetectionConfigResponse)
async def get_gpu_detection_config(
    current_user: User = Depends(get_current_user)
) -> GpuDetectionConfigResponse:
    """
    Get GPU detection configuration.
    
    Returns configuration including:
    - Whether GPU detection is enabled
    - Memory threshold for determining GPU occupation
    - Mock mode status
    
    Requires authentication.
    """
    try:
        lifecycle = get_lifecycle_manager()
        
        config = lifecycle.get_gpu_detection_config()
        
        logger.info(f"GPU detection config retrieved by user {current_user.username}")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to get GPU detection config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve GPU detection configuration: {str(e)}"
        )


@router.get("/count")
async def get_gpu_count(
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Get number of available GPUs.
    
    Returns the count of detected GPUs (excluding CPU fallback).
    
    Requires authentication.
    """
    try:
        lifecycle = get_lifecycle_manager()
        
        response = await lifecycle.detect_gpu_hardware()
        
        logger.info(f"GPU count retrieved by user {current_user.username}: {response.gpu_count}")
        
        return JSONResponse(content={"count": response.gpu_count})
        
    except Exception as e:
        logger.error(f"Failed to get GPU count: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve GPU count: {str(e)}"
        )
