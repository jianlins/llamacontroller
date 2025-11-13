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

logger = logging.getLogger(__name__)

class LifecycleError(Exception):
    """Exception raised for lifecycle management errors."""
    pass

@dataclass
class GpuInstance:
    """单个GPU实例的状态信息"""
    gpu_id: str  # "0", "1", "0,1", "0,1,2", etc.
    port: int
    adapter: LlamaCppAdapter
    model_id: str
    model_config: ModelConfig
    load_time: datetime

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
        
        logger.info("ModelLifecycleManager initialized with multi-GPU support")
    
    def _validate_and_parse_gpu_id(self, gpu_id: Union[int, str]) -> List[int]:
        """
        验证并解析GPU ID字符串
        
        Args:
            gpu_id: GPU ID (如 0, "0", "1", "0,1", "0,1,2")
            
        Returns:
            GPU ID列表 [0], [1], [0, 1], etc.
            
        Raises:
            LifecycleError: GPU ID无效
        """
        # 向后兼容: 支持整数输入
        if isinstance(gpu_id, int):
            gpu_id = str(gpu_id)
        
        # 兼容旧的"both"格式
        if gpu_id == "both":
            logger.warning("gpu_id='both' is deprecated, use '0,1' instead")
            gpu_id = "0,1"
        
        try:
            # 解析逗号分隔的ID
            gpu_ids = [int(x.strip()) for x in str(gpu_id).split(',')]
            
            # 验证范围 (当前支持0-7,为未来扩展预留)
            for gid in gpu_ids:
                if gid < 0 or gid > 7:
                    raise ValueError(f"GPU ID {gid} out of range (0-7)")
            
            # 检查重复
            if len(gpu_ids) != len(set(gpu_ids)):
                raise ValueError("Duplicate GPU IDs")
            
            return sorted(gpu_ids)
        except (ValueError, AttributeError) as e:
            raise LifecycleError(f"Invalid gpu_id '{gpu_id}': {e}")
    
    def _normalize_gpu_id(self, gpu_id: Union[int, str]) -> str:
        """
        标准化GPU ID为字符串格式
        
        Args:
            gpu_id: 原始GPU ID
            
        Returns:
            标准化的字符串 "0", "1", "0,1", etc.
        """
        gpu_list = self._validate_and_parse_gpu_id(gpu_id)
        return ','.join(str(g) for g in gpu_list)
    
    def _check_gpu_conflicts(self, gpu_id: Union[int, str]) -> None:
        """
        检查GPU冲突
        
        Args:
            gpu_id: 要使用的GPU ID
            
        Raises:
            LifecycleError: 存在GPU冲突
        """
        requested_gpus = set(self._validate_and_parse_gpu_id(gpu_id))
        
        for existing_key, instance in self.gpu_instances.items():
            existing_gpus = set(self._validate_and_parse_gpu_id(existing_key))
            
            # 检查是否有重叠
            overlap = requested_gpus & existing_gpus
            if overlap:
                raise LifecycleError(
                    f"GPU conflict: GPU(s) {overlap} already in use by '{existing_key}' "
                    f"(model: '{instance.model_id}')"
                )
    
    def get_port_for_gpu(self, gpu_id: Union[int, str]) -> int:
        """
        根据GPU ID获取端口号,使用主GPU(第一个)的端口
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            端口号
        """
        gpu_list = self._validate_and_parse_gpu_id(gpu_id)
        primary_gpu = gpu_list[0]
        
        # 端口映射: GPU 0->8081, GPU 1->8088
        if primary_gpu == 0:
            return self.config_manager.llama_cpp.gpu_ports.gpu0
        elif primary_gpu == 1:
            return self.config_manager.llama_cpp.gpu_ports.gpu1
        else:
            # 未来扩展: GPU 2->8095, GPU 3->8102, etc.
            return 8081 + (primary_gpu * 7)
    
    def get_gpu_for_model(self, model_id: str) -> Optional[str]:
        """
        查找哪个GPU加载了指定模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            GPU ID字符串，如果模型未加载则返回None
        """
        for gpu_id, instance in self.gpu_instances.items():
            if instance.model_id == model_id:
                return gpu_id
        return None
    
    async def load_model(
        self, 
        model_id: str, 
        gpu_id: Union[int, str] = 0
    ) -> LoadModelResponse:
        """
        在指定GPU上加载模型
        
        Args:
            model_id: 模型ID
            gpu_id: GPU ID (0, 1, 或 "both")
            
        Returns:
            LoadModelResponse
            
        Raises:
            LifecycleError: 加载失败
        """
        logger.info(f"Loading model '{model_id}' on GPU {gpu_id}")
        
        try:
            # 标准化GPU ID
            normalized_gpu_id = self._normalize_gpu_id(gpu_id)
            
            # 获取模型配置
            model_config = self.config_manager.models.get_model(model_id)
            if model_config is None:
                raise LifecycleError(f"Model not found: {model_id}")
            
            # 检查GPU冲突
            self._check_gpu_conflicts(normalized_gpu_id)
            
            # 确定端口
            port = self.get_port_for_gpu(normalized_gpu_id)
            
            # 创建llama.cpp配置副本，使用特定端口
            llama_config = self.config_manager.llama_cpp.model_copy(deep=True)
            llama_config.default_port = port
            
            # 创建新的适配器实例
            adapter = LlamaCppAdapter(llama_config)
            
            # 启动服务器，传递GPU ID
            try:
                adapter.start_server(
                    model_path=model_config.path,
                    params=model_config.parameters,
                    gpu_id=gpu_id
                )
            except AdapterError as e:
                raise LifecycleError(f"Failed to start server: {e}")
            
            # 等待服务器就绪
            logger.info(f"Waiting for server on GPU {gpu_id} to be ready...")
            ready = await self._wait_for_ready(adapter, timeout=60)
            
            if not ready:
                adapter.stop_server()
                raise LifecycleError("Server failed to become ready within timeout")
            
            # 创建并存储GPU实例
            instance = GpuInstance(
                gpu_id=normalized_gpu_id,
                port=port,
                adapter=adapter,
                model_id=model_id,
                model_config=model_config,
                load_time=datetime.now()
            )
            self.gpu_instances[normalized_gpu_id] = instance
            
            # 获取状态
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
        从指定GPU卸载模型
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            UnloadModelResponse
        """
        logger.info(f"Unloading model from GPU {gpu_id}")
        
        # 标准化GPU ID
        normalized_gpu_id = self._normalize_gpu_id(gpu_id)
        
        # 检查该GPU是否有模型
        if normalized_gpu_id not in self.gpu_instances:
            return UnloadModelResponse(
                success=True,
                message=f"No model loaded on GPU {normalized_gpu_id}"
            )
        
        instance = self.gpu_instances[normalized_gpu_id]
        model_id = instance.model_id
        
        try:
            # 停止服务器
            success = instance.adapter.stop_server(graceful=True, timeout=30)
            
            if not success:
                raise LifecycleError(f"Failed to stop server on GPU {gpu_id}")
            
            # 从字典中移除
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
                await asyncio.sleep(1)  # 短暂暁停确保清理完成
            
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
        获取主GPU的模型状态（向后兼容）
        
        Returns:
            ModelStatus
        """
        # 优先返回GPU 0的状态，如果没有则返回"0,1"或GPU 1
        for gpu_key in ["0", "0,1", "1"]:
            if gpu_key in self.gpu_instances:
                instance = self.gpu_instances[gpu_key]
                return await self._get_instance_status(instance)
        
        # 没有任何模型加载
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
        获取特定GPU的状态
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            GpuInstanceStatus或None
        """
        normalized_gpu_id = self._normalize_gpu_id(gpu_id)
        
        if normalized_gpu_id not in self.gpu_instances:
            return None
        
        instance = self.gpu_instances[normalized_gpu_id]
        
        return GpuInstanceStatus(
            gpu_id=normalized_gpu_id,
            port=instance.port,
            model_id=instance.model_id,
            model_name=instance.model_config.name,
            status=instance.adapter.get_status(),
            loaded_at=instance.load_time,
            uptime_seconds=instance.adapter.get_uptime_seconds(),
            pid=instance.adapter.get_pid()
        )
    
    async def get_all_gpu_statuses(self) -> AllGpuStatus:
        """
        获取所有GPU的状态
        
        Returns:
            AllGpuStatus
        """
        return AllGpuStatus(
            gpu0=await self.get_gpu_status("0"),
            gpu1=await self.get_gpu_status("1"),
            both=await self.get_gpu_status("0,1")
        )
    
    async def _get_instance_status(self, instance: GpuInstance) -> ModelStatus:
        """
        从GPU实例获取ModelStatus
        
        Args:
            instance: GPU实例
            
        Returns:
            ModelStatus
        """
        return ModelStatus(
            model_id=instance.model_id,
            model_name=instance.model_config.name,
            status=instance.adapter.get_status(),
            loaded_at=instance.load_time,
            memory_usage_mb=None,  # TODO: 实现内存跟踪
            uptime_seconds=instance.adapter.get_uptime_seconds(),
            pid=instance.adapter.get_pid(),
            host=self.config_manager.llama_cpp.default_host,
            port=instance.port,
        )
    
    def get_current_model(self) -> Optional[ModelConfig]:
        """
        获取当前加载的模型配置（向后兼容）
        返回第一个找到的模型
        
        Returns:
            ModelConfig或None
        """
        for gpu_key in ["0", "0,1", "1"]:
            if gpu_key in self.gpu_instances:
                return self.gpu_instances[gpu_key].model_config
        return None
    
    async def healthcheck(self) -> HealthCheckResponse:
        """
        检查是否有健康的模型实例（向后兼容）
        
        Returns:
            HealthCheckResponse
        """
        # 检查所有GPU实例
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
        
        # 没有健康的实例
        return HealthCheckResponse(
            healthy=False,
            status=ProcessStatus.STOPPED,
            message="No healthy model instances running",
            uptime_seconds=None
        )
    
    def get_available_models(self) -> List[ModelInfo]:
        """
        获取可用模型列表
        
        Returns:
            ModelInfo列表
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
        获取可用模型ID列表
        
        Returns:
            模型ID列表
        """
        return self.config_manager.models.get_model_ids()
    
    async def _wait_for_ready(
        self, 
        adapter: LlamaCppAdapter, 
        timeout: int = 60
    ) -> bool:
        """
        等待llama-server就绪
        
        Args:
            adapter: 适配器实例
            timeout: 超时时间（秒）
            
        Returns:
            是否就绪
        """
        start_time = asyncio.get_event_loop().time()
        check_interval = 1.0
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            is_healthy = await adapter.is_healthy()
            
            if is_healthy:
                logger.info("Server is ready")
                return True
            
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Server did not become ready within {timeout}s")
        return False
    
    async def get_server_logs(
        self, 
        gpu_id: Union[int, str] = None, 
        lines: int = 300
    ) -> List[str]:
        """
        获取指定GPU的服务器日志，如果gpu_id为None则返回第一个可用实例的日志
        
        Args:
            gpu_id: GPU ID (None表示自动选择第一个可用的)
            lines: 日志行数
            
        Returns:
            日志行列表
        """
        logger.info(f"get_server_logs called with gpu_id={gpu_id}, lines={lines}")
        logger.info(f"Current gpu_instances: {list(self.gpu_instances.keys())}")
        
        # 如果没有指定GPU，尝试查找第一个可用的实例
        if gpu_id is None:
            if not self.gpu_instances:
                logger.warning("No GPU instances loaded")
                return ["No models currently loaded"]
            # 返回第一个可用实例的日志
            gpu_id = next(iter(self.gpu_instances.keys()))
            logger.info(f"Auto-selected GPU: {gpu_id}")
        
        normalized_gpu_id = self._normalize_gpu_id(gpu_id)
        logger.info(f"Normalized GPU ID: {normalized_gpu_id}")
        
        if normalized_gpu_id not in self.gpu_instances:
            # 列出当前加载的GPU
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
    
    def __del__(self):
        """清理时停止所有实例"""
        if self.gpu_instances:
            logger.warning(
                f"LifecycleManager being destroyed with {len(self.gpu_instances)} loaded models"
            )
            # 注意：不能在__del__中使用async
