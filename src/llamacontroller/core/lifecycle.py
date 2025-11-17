"""
Model lifecycle manager for high-level model operations.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Union
from datetime import datetime
from dataclasses import dataclass

from .config import ConfigManager
from .adapter import LlamaCppAdapter, AdapterError
from .gpu_detector import GpuDetector, GpuStatus as GpuDetectorStatus, GpuProcessInfo as GpuDetectorProcessInfo
from .process_registry import ProcessRegistry
from ..models.config import ModelConfig
from ..models.lifecycle import (
    ProcessStatus,
    ModelStatus,
    LoadModelResponse,
    UnloadModelResponse,
    SwitchModelResponse,
    ModelInfo,
    HealthCheckResponse,
    GpuInstanceStatus,
    AllGpuStatus,
)
from ..models.gpu import (
    GpuStatusResponse,
    GpuProcessInfoResponse,
    AllGpuStatusResponse,
    GpuDetectionConfigResponse,
)

logger = logging.getLogger(__name__)

class LifecycleError(Exception):
    """Exception raised for lifecycle management errors."""
    pass

@dataclass
class GpuInstance:
    """Status information for a single GPU instance"""
    gpu_id: str  # "0", "1", "0,1", "0,1,2", etc.
    port: int
    adapter: LlamaCppAdapter
    model_id: str
    model_config: ModelConfig
    load_time: datetime
    memory_used_mb: int = 0
    memory_total_mb: int = 0

class ModelLifecycleManager:
    """
    High-level model lifecycle management with multi-GPU support.
    
    Provides operations for loading, unloading, and switching models
    across multiple GPUs, managing separate llama.cpp process instances.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the lifecycle manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.gpu_instances: Dict[str, GpuInstance] = {}
        
        # Initialize GPU detector
        gpu_config = config_manager.llama_cpp.gpu_detection
        self.gpu_detector = GpuDetector(
            memory_threshold_mb=gpu_config.memory_threshold_mb
        )
        
        # Initialize process registry
        self.process_registry = ProcessRegistry()
        self.process_registry.load()
        
        # Recover tracked processes on startup
        self._recover_processes()
        
        logger.info("ModelLifecycleManager initialized with multi-GPU support and process registry")
    
    def _validate_and_parse_gpu_id(self, gpu_id: Union[int, str]) -> List[int]:
        """
        Validate and parse GPU ID string
        
        Args:
            gpu_id: GPU ID (e.g., 0, "0", "1", "0,1", "0,1,2")
            
        Returns:
            GPU ID list [0], [1], [0, 1], etc.
            
        Raises:
            LifecycleError: Invalid GPU ID
        """
        # Backward compatibility: support integer input
        if isinstance(gpu_id, int):
            gpu_id = str(gpu_id)
        
        # Compatibility with old "both" format
        if gpu_id == "both":
            logger.warning("gpu_id='both' is deprecated, use '0,1' instead")
            gpu_id = "0,1"
        
        try:
            # Parse comma-separated IDs
            gpu_ids = [int(x.strip()) for x in str(gpu_id).split(',')]
            
            # Validate range (currently supports 0-7, reserved for future expansion)
            for gid in gpu_ids:
                if gid < 0 or gid > 7:
                    raise ValueError(f"GPU ID {gid} out of range (0-7)")
            
            # Check for duplicates
            if len(gpu_ids) != len(set(gpu_ids)):
                raise ValueError("Duplicate GPU IDs")
            
            return sorted(gpu_ids)
        except (ValueError, AttributeError) as e:
            raise LifecycleError(f"Invalid gpu_id '{gpu_id}': {e}")
    
    def _normalize_gpu_id(self, gpu_id: Union[int, str]) -> str:
        """
        Normalize GPU ID to string format
        
        Args:
            gpu_id: Original GPU ID
            
        Returns:
            Normalized string "0", "1", "0,1", etc.
        """
        gpu_list = self._validate_and_parse_gpu_id(gpu_id)
        return ','.join(str(g) for g in gpu_list)
    
    def _recover_processes(self) -> None:
        """Recover tracked processes on startup."""
        logger.info("Recovering tracked processes from registry...")
        
        verification_results = self.process_registry.verify_all_processes()
        
        for gpu_id, is_running in verification_results.items():
            if is_running:
                entry = self.process_registry.get_process(gpu_id)
                if entry:
                    logger.info(
                        f"Recovered running process: GPU {gpu_id}, "
                        f"PID {entry.pid}, Model {entry.model_id}"
                    )
                    # Note: We track that the process exists but don't reattach to it
                    # The user will need to manually unload these processes if needed
            else:
                logger.warning(f"Process for GPU {gpu_id} is no longer running, cleaning up registry")
                self.process_registry.unregister_process(gpu_id)
        
        recovered_count = len([v for v in verification_results.values() if v])
        if recovered_count > 0:
            logger.info(f"Recovered {recovered_count} running processes")
    
    def _check_gpu_conflicts(self, gpu_id: Union[int, str]) -> None:
        """
        Check for GPU conflicts
        
        Args:
            gpu_id: GPU ID to use
            
        Raises:
            LifecycleError: GPU conflict exists
        """
        requested_gpus = set(self._validate_and_parse_gpu_id(gpu_id))
        
        for existing_key, instance in self.gpu_instances.items():
            existing_gpus = set(self._validate_and_parse_gpu_id(existing_key))
            
            # Check for overlap
            overlap = requested_gpus & existing_gpus
            if overlap:
                raise LifecycleError(
                    f"GPU conflict: GPU(s) {overlap} already in use by '{existing_key}' "
                    f"(model: '{instance.model_id}')"
                )
    
    def get_port_for_gpu(self, gpu_id: Union[int, str]) -> int:
        """
        Get port number based on GPU ID, using the primary GPU's (first) port
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            Port number
        """
        gpu_list = self._validate_and_parse_gpu_id(gpu_id)
        primary_gpu = gpu_list[0]
        
        # Port mapping: GPU 0->8081, GPU 1->8088
        if primary_gpu == 0:
            return self.config_manager.llama_cpp.gpu_ports.gpu0
        elif primary_gpu == 1:
            return self.config_manager.llama_cpp.gpu_ports.gpu1
        else:
            # Future expansion: GPU 2->8095, GPU 3->8102, etc.
            return 8081 + (primary_gpu * 7)
    
    def get_gpu_for_model(self, model_id: str) -> Optional[str]:
        """
        Find which GPU has loaded the specified model
        
        Args:
            model_id: Model ID
            
        Returns:
            GPU ID string, or None if model is not loaded
        """
        for gpu_id, instance in self.gpu_instances.items():
            if instance.model_id == model_id:
                return gpu_id
        return None
    
    def _query_gpu_memory(self, gpu_id: str) -> Dict[str, int]:
        """
        Query GPU memory usage for specific GPU(s).
        
        Args:
            gpu_id: GPU ID string (e.g., "0", "1", "0,1")
            
        Returns:
            Dict with 'memory_used' and 'memory_total' in MiB
        """
        try:
            # Get GPU IDs as list
            gpu_ids = self._validate_and_parse_gpu_id(gpu_id)
            
            # Query GPU detector for current status
            gpu_statuses = self.gpu_detector.detect_gpus()
            
            # For multi-GPU, sum memory usage
            total_used = 0
            total_capacity = 0
            
            for gid in gpu_ids:
                gpu_status = next((g for g in gpu_statuses if g.index == gid), None)
                if gpu_status:
                    total_used += gpu_status.memory_used
                    total_capacity += gpu_status.memory_total
            
            return {
                'memory_used': total_used,
                'memory_total': total_capacity
            }
        except Exception as e:
            logger.warning(f"Failed to query GPU memory for {gpu_id}: {e}")
            return {'memory_used': 0, 'memory_total': 0}
    
    async def load_model(
        self, 
        model_id: str, 
        gpu_id: Union[int, str] = 0
    ) -> LoadModelResponse:
        """
        Load model on specified GPU
        
        Args:
            model_id: Model ID
            gpu_id: GPU ID (0, 1, or "both")
            
        Returns:
            LoadModelResponse
            
        Raises:
            LifecycleError: Load failed
        """
        logger.info(f"Loading model '{model_id}' on GPU {gpu_id}")
        
        try:
            # Normalize GPU ID
            normalized_gpu_id = self._normalize_gpu_id(gpu_id)
            
            # Get model configuration
            model_config = self.config_manager.models.get_model(model_id)
            if model_config is None:
                raise LifecycleError(f"Model not found: {model_id}")
            
            # Check for GPU conflicts
            self._check_gpu_conflicts(normalized_gpu_id)
            
            # Determine port
            port = self.get_port_for_gpu(normalized_gpu_id)
            
            # Create llama.cpp config copy with specific port
            llama_config = self.config_manager.llama_cpp.model_copy(deep=True)
            llama_config.default_port = port
            
            # Create new adapter instance
            adapter = LlamaCppAdapter(llama_config)
            
            # Start server, pass GPU ID
            try:
                adapter.start_server(
                    model_path=model_config.path,
                    params=model_config.parameters,
                    gpu_id=gpu_id
                )
            except AdapterError as e:
                raise LifecycleError(f"Failed to start server: {e}")
            
            # Wait for server to be ready
            logger.info(f"Waiting for server on GPU {gpu_id} to be ready...")
            ready = await self._wait_for_ready(adapter, timeout=60)
            
            if not ready:
                adapter.stop_server()
                raise LifecycleError("Server failed to become ready within timeout")
            
            # Create and store GPU instance
            instance = GpuInstance(
                gpu_id=normalized_gpu_id,
                port=port,
                adapter=adapter,
                model_id=model_id,
                model_config=model_config,
                load_time=datetime.now()
            )
            self.gpu_instances[normalized_gpu_id] = instance
            
            # Register process in registry
            pid = adapter.get_pid()
            if pid:
                # Get the command line from the adapter (we'll need to add this method)
                command_line = [
                    str(llama_config.executable_path),
                    "-m", model_config.path,
                    "--host", llama_config.default_host,
                    "--port", str(port)
                ]
                
                self.process_registry.register_process(
                    gpu_id=normalized_gpu_id,
                    pid=pid,
                    model_id=model_id,
                    model_name=model_config.name,
                    model_path=model_config.path,
                    port=port,
                    command_line=command_line
                )
            
            # Query GPU memory usage after successful load
            memory_info = self._query_gpu_memory(normalized_gpu_id)
            instance.memory_used_mb = memory_info['memory_used']
            instance.memory_total_mb = memory_info['memory_total']
            
            logger.info(
                f"Model '{model_id}' loaded on GPU {normalized_gpu_id}: "
                f"{memory_info['memory_used']}MiB / {memory_info['memory_total']}MiB"
            )
            
            # Get status
            status = await self._get_instance_status(instance)
            
            logger.info(f"Model '{model_id}' loaded successfully on GPU {normalized_gpu_id}")
            
            return LoadModelResponse(
                success=True,
                model_id=model_id,
                message=f"Model '{model_config.name}' loaded on GPU {normalized_gpu_id}",
                status=status
            )
            
        except LifecycleError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading model: {e}")
            raise LifecycleError(f"Failed to load model: {e}")
    
    async def unload_model(self, gpu_id: Union[int, str]) -> UnloadModelResponse:
        """
        Unload model from specified GPU
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            UnloadModelResponse
        """
        logger.info(f"Unloading model from GPU {gpu_id}")
        
        # Normalize GPU ID
        normalized_gpu_id = self._normalize_gpu_id(gpu_id)
        
        # Check if GPU has a model loaded
        if normalized_gpu_id not in self.gpu_instances:
            return UnloadModelResponse(
                success=True,
                message=f"No model loaded on GPU {normalized_gpu_id}"
            )
        
        instance = self.gpu_instances[normalized_gpu_id]
        model_id = instance.model_id
        
        try:
            # Stop server
            success = instance.adapter.stop_server(graceful=True, timeout=30)
            
            if not success:
                raise LifecycleError(f"Failed to stop server on GPU {gpu_id}")
            
            # Unregister from process registry
            self.process_registry.unregister_process(normalized_gpu_id)
            
            # Remove from dictionary
            del self.gpu_instances[normalized_gpu_id]
            
            logger.info(f"Model '{model_id}' unloaded from GPU {normalized_gpu_id}")
            
            return UnloadModelResponse(
                success=True,
                message=f"Model '{model_id}' unloaded from GPU {normalized_gpu_id}"
            )
            
        except Exception as e:
            logger.error(f"Error unloading model from GPU {gpu_id}: {e}")
            raise LifecycleError(f"Failed to unload model: {e}")
    
    async def switch_model(
        self, 
        new_model_id: str, 
        gpu_id: Union[int, str] = 0
    ) -> SwitchModelResponse:
        """
        在指定GPU上切换模型
        
        Args:
            new_model_id: 新模型ID
            gpu_id: GPU ID
            
        Returns:
            SwitchModelResponse
        """
        logger.info(f"Switching to model '{new_model_id}' on GPU {gpu_id}")
        
        try:
            # 标准化GPU ID
            normalized_gpu_id = self._normalize_gpu_id(gpu_id)
            
            # 验证新模型存在
            new_model_config = self.config_manager.models.get_model(new_model_id)
            if new_model_config is None:
                raise LifecycleError(f"Model not found: {new_model_id}")
            
            # 获取旧模型ID
            old_model_id = None
            if normalized_gpu_id in self.gpu_instances:
                old_model_id = self.gpu_instances[normalized_gpu_id].model_id
                
                # 如果是同一个模型，直接返回
                if old_model_id == new_model_id:
                    status = await self._get_instance_status(self.gpu_instances[normalized_gpu_id])
                    return SwitchModelResponse(
                        success=True,
                        old_model_id=old_model_id,
                        new_model_id=new_model_id,
                        message=f"Model '{new_model_id}' is already loaded on GPU {normalized_gpu_id}",
                        status=status
                    )
                
                # 卸载旧模型
                logger.info(f"Unloading current model '{old_model_id}' from GPU {normalized_gpu_id}")
                await self.unload_model(normalized_gpu_id)
                await asyncio.sleep(1)  # Brief pause to ensure cleanup completes
            
            # 加载新模型
            logger.info(f"Loading new model '{new_model_id}' on GPU {normalized_gpu_id}")
            load_response = await self.load_model(new_model_id, normalized_gpu_id)
            
            if not load_response.success:
                raise LifecycleError(f"Failed to load new model: {load_response.message}")
            
            logger.info(f"Successfully switched to model '{new_model_id}' on GPU {normalized_gpu_id}")
            
            return SwitchModelResponse(
                success=True,
                old_model_id=old_model_id,
                new_model_id=new_model_id,
                message=f"Successfully switched to '{new_model_config.name}' on GPU {normalized_gpu_id}",
                status=load_response.status
            )
            
        except LifecycleError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error switching model: {e}")
            raise LifecycleError(f"Failed to switch model: {e}")
    
    async def get_status(self) -> ModelStatus:
        """
        Get model status of primary GPU (backward compatible)
        
        Returns:
            ModelStatus
        """
        # Prioritize GPU 0 status, otherwise return "0,1" or GPU 1
        for gpu_key in ["0", "0,1", "1"]:
            if gpu_key in self.gpu_instances:
                instance = self.gpu_instances[gpu_key]
                return await self._get_instance_status(instance)
        
        # No models loaded
        return ModelStatus(
            model_id=None,
            model_name=None,
            status=ProcessStatus.STOPPED,
            loaded_at=None,
            memory_usage_mb=None,
            uptime_seconds=None,
            pid=None,
            host=self.config_manager.llama_cpp.default_host,
            port=self.config_manager.llama_cpp.gpu_ports.gpu0,
        )
    
    async def get_gpu_status(
        self, 
        gpu_id: Union[int, str]
    ) -> Optional[GpuInstanceStatus]:
        """
        Get status of a specific GPU
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            GpuInstanceStatus or None
        """
        normalized_gpu_id = self._normalize_gpu_id(gpu_id)
        logger.info(f"get_gpu_status called for gpu_id={gpu_id}, normalized={normalized_gpu_id}")
        logger.info(f"Available gpu_instances: {list(self.gpu_instances.keys())}")
        
        if normalized_gpu_id not in self.gpu_instances:
            logger.info(f"GPU {normalized_gpu_id} not found in instances, returning None")
            return None
        
        instance = self.gpu_instances[normalized_gpu_id]
        logger.info(f"Found instance for GPU {normalized_gpu_id}: model={instance.model_id}, port={instance.port}")
        
        # Query current memory (fresh data on every status check)
        memory_info = self._query_gpu_memory(normalized_gpu_id)
        
        status_obj = GpuInstanceStatus(
            gpu_id=normalized_gpu_id,
            port=instance.port,
            model_id=instance.model_id,
            model_name=instance.model_config.name,
            status=instance.adapter.get_status(),
            loaded_at=instance.load_time,
            uptime_seconds=instance.adapter.get_uptime_seconds(),
            pid=instance.adapter.get_pid(),
            memory_used_mb=memory_info['memory_used'],
            memory_total_mb=memory_info['memory_total']
        )
        logger.info(f"Returning status for GPU {normalized_gpu_id}: {status_obj}")
        return status_obj
    
    async def get_all_gpu_statuses(self) -> Dict[str, Optional[GpuInstanceStatus]]:
        """
        Get status of all loaded GPUs
        
        Returns:
            Dictionary mapping GPU ID strings to GpuInstanceStatus
            Keys are normalized GPU IDs: "0", "1", "0,1", "0,1,2" etc.
        """
        result = {}
        
        # Return status for all loaded GPU instances
        # Use GPU ID directly as key (no "gpu" prefix)
        for gpu_id in self.gpu_instances.keys():
            result[gpu_id] = await self.get_gpu_status(gpu_id)
        
        logger.info(f"get_all_gpu_statuses - returning {len(result)} statuses")
        logger.info(f"get_all_gpu_statuses - keys: {list(result.keys())}")
        
        return result
    
    async def _get_instance_status(self, instance: GpuInstance) -> ModelStatus:
        """
        Get ModelStatus from GPU instance
        
        Args:
            instance: GPU instance
            
        Returns:
            ModelStatus
        """
        return ModelStatus(
            model_id=instance.model_id,
            model_name=instance.model_config.name,
            status=instance.adapter.get_status(),
            loaded_at=instance.load_time,
            memory_usage_mb=None,  # TODO: Implement memory tracking
            uptime_seconds=instance.adapter.get_uptime_seconds(),
            pid=instance.adapter.get_pid(),
            host=self.config_manager.llama_cpp.default_host,
            port=instance.port,
        )
    
    def get_current_model(self) -> Optional[ModelConfig]:
        """
        Get currently loaded model configuration (backward compatible)
        Returns the first model found
        
        Returns:
            ModelConfig or None
        """
        for gpu_key in ["0", "0,1", "1"]:
            if gpu_key in self.gpu_instances:
                return self.gpu_instances[gpu_key].model_config
        return None
    
    async def healthcheck(self) -> HealthCheckResponse:
        """
        Check if there are healthy model instances (backward compatible)
        
        Returns:
            HealthCheckResponse
        """
        # Check all GPU instances
        for instance in self.gpu_instances.values():
            status = instance.adapter.get_status()
            
            if status == ProcessStatus.RUNNING:
                is_healthy = await instance.adapter.is_healthy()
                uptime = instance.adapter.get_uptime_seconds()
                
                if is_healthy:
                    return HealthCheckResponse(
                        healthy=True,
                        status=status,
                        message=f"Model '{instance.model_id}' on GPU {instance.gpu_id} is healthy",
                        uptime_seconds=uptime
                    )
        
        # No healthy instances
        return HealthCheckResponse(
            healthy=False,
            status=ProcessStatus.STOPPED,
            message="No healthy model instances running",
            uptime_seconds=None
        )
    
    def get_available_models(self) -> List[ModelInfo]:
        """
        Get list of available models
        
        Returns:
            List of ModelInfo
        """
        models = []
        loaded_model_ids = {inst.model_id for inst in self.gpu_instances.values()}
        
        for model_config in self.config_manager.models.models:
            is_loaded = model_config.id in loaded_model_ids
            status = "loaded" if is_loaded else "available"
            
            models.append(ModelInfo(
                id=model_config.id,
                name=model_config.name,
                path=model_config.path,
                status=status,
                loaded=is_loaded,
                description=model_config.metadata.description,
                parameter_count=model_config.metadata.parameter_count,
                quantization=model_config.metadata.quantization,
            ))
        
        return models
    
    def get_model_ids(self) -> List[str]:
        """
        Get list of available model IDs
        
        Returns:
            List of model IDs
        """
        return self.config_manager.models.get_model_ids()
    
    async def _wait_for_ready(
        self, 
        adapter: LlamaCppAdapter, 
        timeout: int = 60
    ) -> bool:
        """
        Wait for llama-server to be ready
        
        Args:
            adapter: Adapter instance
            timeout: Timeout in seconds
            
        Returns:
            Whether ready
        """
        start_time = asyncio.get_event_loop().time()
        check_interval = 1.0
        last_log_time = 0
        
        logger.info(f"Waiting for server to be ready (timeout: {timeout}s)...")
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Check if process is still alive
            if adapter.process and adapter.process.poll() is not None:
                logger.error("Server process died during startup")
                # Print last few log lines to help diagnose
                logs = adapter.get_logs(lines=10)
                if logs:
                    logger.error("Last log lines from server:")
                    for log_line in logs[-10:]:
                        logger.error(f"  {log_line}")
                return False
            
            # Try health check
            is_healthy = await adapter.is_healthy()
            
            if is_healthy:
                logger.info(f"Server is ready (took {elapsed:.1f}s)")
                return True
            
            # Log progress every 5 seconds
            if elapsed - last_log_time >= 5:
                logger.info(f"Still waiting for server... ({elapsed:.0f}s elapsed)")
                last_log_time = elapsed
            
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Server did not become ready within {timeout}s")
        # Print last few log lines to help diagnose
        logs = adapter.get_logs(lines=20)
        if logs:
            logger.warning("Last log lines from server:")
            for log_line in logs[-20:]:
                logger.warning(f"  {log_line}")
        return False
    
    async def get_server_logs(
        self, 
        gpu_id: Optional[Union[int, str]] = None, 
        lines: int = 300
    ) -> List[str]:
        """
        Get server logs for specified GPU, or first available instance if gpu_id is None
        
        Args:
            gpu_id: GPU ID (None means auto-select first available)
            lines: Number of log lines
            
        Returns:
            List of log lines
        """
        logger.info(f"get_server_logs called with gpu_id={gpu_id}, lines={lines}")
        logger.info(f"Current gpu_instances: {list(self.gpu_instances.keys())}")
        
        # If no GPU specified, try to find first available instance
        if gpu_id is None:
            if not self.gpu_instances:
                logger.warning("No GPU instances loaded")
                return ["No models currently loaded"]
            # Return logs from first available instance
            gpu_id = next(iter(self.gpu_instances.keys()))
            logger.info(f"Auto-selected GPU: {gpu_id}")
        
        normalized_gpu_id = self._normalize_gpu_id(gpu_id)
        logger.info(f"Normalized GPU ID: {normalized_gpu_id}")
        
        if normalized_gpu_id not in self.gpu_instances:
            # List currently loaded GPUs
            loaded_gpus = list(self.gpu_instances.keys())
            logger.warning(f"GPU {normalized_gpu_id} not found in loaded instances: {loaded_gpus}")
            if loaded_gpus:
                return [
                    f"No model loaded on GPU {normalized_gpu_id}",
                    f"Models are currently loaded on: {', '.join(loaded_gpus)}"
                ]
            return [f"No model loaded on GPU {normalized_gpu_id}"]
        
        instance = self.gpu_instances[normalized_gpu_id]
        lines = min(lines, 300)
        logger.info(f"Getting logs from GPU {normalized_gpu_id}, model: {instance.model_id}")
        log_lines = instance.adapter.get_logs(lines=lines)
        logger.info(f"Retrieved {len(log_lines)} log lines")
        return log_lines
    
    async def detect_gpu_hardware(self) -> AllGpuStatusResponse:
        """
        Detect GPU hardware and return status information.
        
        This combines hardware detection with loaded model information.
        
        Returns:
            AllGpuStatusResponse with GPU statuses
        """
        print(f"[DEBUG] detect_gpu_hardware() called in lifecycle.py", flush=True)
        
        # Update GPU detector with loaded model mappings
        for gpu_id, instance in self.gpu_instances.items():
            self.gpu_detector.set_model_mapping(gpu_id, instance.model_config.name)
            print(f"[DEBUG] Set model mapping: GPU {gpu_id} -> {instance.model_config.name}", flush=True)
        
        # Detect GPUs
        print(f"[DEBUG] About to call gpu_detector.detect_gpus()...", flush=True)
        detected_gpus = self.gpu_detector.detect_gpus()
        print(f"[DEBUG] detect_gpus() returned {len(detected_gpus)} GPUs", flush=True)
        
        # Convert to response format
        gpu_responses = []
        for gpu_status in detected_gpus:
            # Convert process info if present
            process_info_response = None
            if gpu_status.process_info:
                process_info_response = [
                    GpuProcessInfoResponse(
                        gpu_index=p.gpu_index,
                        pid=p.pid,
                        process_name=p.process_name,
                        used_memory=p.used_memory
                    )
                    for p in gpu_status.process_info
                ]
            
            gpu_responses.append(GpuStatusResponse(
                index=gpu_status.index,
                state=gpu_status.state,
                model_name=gpu_status.model_name,
                process_info=process_info_response,
                select_enabled=gpu_status.select_enabled,
                memory_used=gpu_status.memory_used,
                memory_total=gpu_status.memory_total
            ))
        
        # Count non-CPU GPUs
        gpu_count = len([g for g in detected_gpus if g.index >= 0])
        
        return AllGpuStatusResponse(
            gpus=gpu_responses,
            gpu_count=gpu_count,
            detection_enabled=self.config_manager.llama_cpp.gpu_detection.enabled
        )
    
    def get_gpu_detection_config(self) -> GpuDetectionConfigResponse:
        """
        Get GPU detection configuration.

        Returns:
            GpuDetectionConfigResponse
        """
        config = self.config_manager.llama_cpp.gpu_detection
        return GpuDetectionConfigResponse(
            enabled=config.enabled,
            memory_threshold_mb=config.memory_threshold_mb
        )
    
    def __del__(self):
        """Stop all instances during cleanup"""
        if self.gpu_instances:
            logger.warning(
                f"LifecycleManager being destroyed with {len(self.gpu_instances)} loaded models"
            )
            # Note: Cannot use async in __del__
