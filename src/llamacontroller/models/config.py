"""
Pydantic models for configuration validation.
"""

from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class GpuPortsConfig(BaseModel):
    """GPU port mapping configuration."""
    
    gpu0: int = Field(default=8081, ge=1, le=65535, description="Port for GPU 0")
    gpu1: int = Field(default=8088, ge=1, le=65535, description="Port for GPU 1")
    both: int = Field(default=8081, ge=1, le=65535, description="Port when using both GPUs")

class GpuDetectionConfig(BaseModel):
    """GPU detection configuration."""
    
    enabled: bool = Field(default=True, description="Enable GPU detection")
    memory_threshold_mb: int = Field(default=30, ge=1, description="Memory threshold in MB to consider GPU occupied")
    mock_mode: bool = Field(default=False, description="Enable mock mode for testing without nvidia-smi")
    mock_data_path: str = Field(default="data/gpu.txt", description="Path to mock nvidia-smi output file")

class LlamaCppConfig(BaseModel):
    """Configuration for llama.cpp executable."""
    
    executable_path: str = Field(..., description="Path to llama-server executable")
    default_host: str = Field(default="127.0.0.1", description="Default host for llama-server")
    default_port: int = Field(default=8080, ge=1, le=65535, description="Default port for llama-server (deprecated, use gpu_ports)")
    gpu_ports: GpuPortsConfig = Field(default_factory=GpuPortsConfig, description="Port mapping for GPU instances")
    gpu_detection: GpuDetectionConfig = Field(default_factory=GpuDetectionConfig, description="GPU detection configuration")
    api_key: Optional[str] = Field(
        default=None, 
        description="API key for llama-server (optional). If set, llama-server will require this key for authentication. "
                    "This is used internally - users authenticate with LlamaController tokens."
    )
    log_level: str = Field(default="info", description="Log level for llama-server")
    restart_on_crash: bool = Field(default=True, description="Auto-restart on crash")
    max_restart_attempts: int = Field(default=3, ge=0, description="Max restart attempts")
    timeout_seconds: int = Field(default=300, ge=1, description="Timeout for operations")
    
    @field_validator("executable_path")
    @classmethod
    def validate_executable_path(cls, v: str) -> str:
        """Validate that executable path exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"llama-server executable not found at: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.lower()

class ModelParameters(BaseModel):
    """
    Parameters for model inference.
    
    This now supports flexible parameter configuration using llama-serve's native
    parameter names. Parameters can be:
    1. Key-value pairs: {"temp": 0.7, "c": 24000}
    2. Boolean flags (use null/None): {"context-shift": null}
    3. List values for multi-value params: {"system-prompt-file": ["file1.txt", "file2.txt"]}
    
    The old structured format is deprecated but still supported for backwards compatibility.
    """
    
    # Deprecated: Old structured parameters (kept for backwards compatibility)
    n_ctx: Optional[int] = Field(default=None, ge=128, description="[DEPRECATED] Use 'c' or 'ctx-size' in cli_params")
    n_gpu_layers: Optional[int] = Field(default=None, ge=0, description="[DEPRECATED] Use 'n-gpu-layers' or 'ngl' in cli_params")
    n_threads: Optional[int] = Field(default=None, ge=1, description="[DEPRECATED] Use 'threads' or 't' in cli_params")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="[DEPRECATED] Use 'temp' in cli_params")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="[DEPRECATED] Use 'top-p' in cli_params")
    top_k: Optional[int] = Field(default=None, ge=0, description="[DEPRECATED] Use 'top-k' in cli_params")
    repeat_penalty: Optional[float] = Field(default=None, ge=0.0, description="[DEPRECATED] Use 'repeat-penalty' in cli_params")
    
    # New flexible parameter system
    cli_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible llama-serve CLI parameters. Use llama-serve's native parameter names. "
                    "Set value to null for boolean flags (e.g., {'context-shift': null})"
    )
    
    def get_cli_arguments(self) -> List[str]:
        """
        Convert parameters to CLI arguments for llama-serve.
        
        Returns:
            List of command line arguments
        """
        args = []
        
        # Map of short-form parameters that should use single dash
        # Based on llama-server --help output
        short_params = {
            'c', 't', 'n', 'b', 'e', 's', 'l', 'j', 'r', 'v', 'm', 'a',  # Single letter
            'ngl', 'tb', 'ub', 'np', 'sm', 'ts', 'mg', 'mu', 'sp', 'cb', 'to',  # Multi-letter but short form
            'fa', 'nr', 'dt', 'lv', 'dev', 'hf', 'dr', 'td', 'cd', 'md', 'mv',  # More short forms
            'nkvo', 'ctk', 'ctv', 'nocb', 'ngld', 'cmoe', 'ncmoe', 'cmoed', 'ncmoed',
            'hfr', 'hff', 'hft', 'hfd', 'hfv', 'hffv', 'hfrd', 'hfrv', 'jf',
            'otd', 'sps', 'tbd', 'devd', 'kvu'
        }
        
        # Process new cli_params (preferred)
        for key, value in self.cli_params.items():
            # Determine if this should use single dash or double dash
            # Short params (in our map) use single dash, others use double dash
            if key in short_params:
                flag_prefix = f"-{key}"
            else:
                flag_prefix = f"--{key}"
            
            # Handle boolean flags (value is None/null)
            if value is None:
                args.append(flag_prefix)
            # Handle list values (multiple values for same parameter)
            elif isinstance(value, list):
                if len(value) == 0:  # Empty list also treated as boolean flag
                    args.append(flag_prefix)
                else:
                    for item in value:
                        args.extend([flag_prefix, str(item)])
            # Handle regular key-value pairs
            else:
                args.extend([flag_prefix, str(value)])
        
        # Backwards compatibility: Add old-style parameters if not in cli_params
        if self.n_ctx is not None and 'c' not in self.cli_params and 'ctx-size' not in self.cli_params:
            args.extend(["--ctx-size", str(self.n_ctx)])
        
        if self.n_gpu_layers is not None and 'ngl' not in self.cli_params and 'n-gpu-layers' not in self.cli_params:
            args.extend(["--n-gpu-layers", str(self.n_gpu_layers)])
        
        if self.n_threads is not None and 't' not in self.cli_params and 'threads' not in self.cli_params:
            args.extend(["--threads", str(self.n_threads)])
        
        if self.temperature is not None and 'temp' not in self.cli_params:
            args.extend(["--temp", str(self.temperature)])
        
        if self.top_p is not None and 'top-p' not in self.cli_params:
            args.extend(["--top-p", str(self.top_p)])
        
        if self.top_k is not None and 'top-k' not in self.cli_params:
            args.extend(["--top-k", str(self.top_k)])
        
        if self.repeat_penalty is not None and 'repeat-penalty' not in self.cli_params:
            args.extend(["--repeat-penalty", str(self.repeat_penalty)])
        
        return args

class ModelMetadata(BaseModel):
    """Metadata about a model."""
    
    description: str = Field(default="", description="Model description")
    parameter_count: str = Field(default="", description="Model parameter count (e.g., '7B', '13B')")
    quantization: str = Field(default="", description="Quantization type (e.g., 'Q4_K_M')")
    family: str = Field(default="", description="Model family (e.g., 'llama', 'mistral')")
    capabilities: List[str] = Field(default_factory=list, description="Model capabilities")

class GpuConfig(BaseModel):
    """GPU configuration for model loading."""
    
    mode: Literal["single", "both"] = Field(default="single", description="GPU mode: 'single' or 'both'")
    gpu_id: int = Field(default=0, ge=0, le=1, description="GPU ID when mode is 'single' (0 or 1)")
    
    @field_validator("gpu_id")
    @classmethod
    def validate_gpu_id(cls, v: int, info) -> int:
        """Validate GPU ID based on mode."""
        # gpu_id is only used when mode is "single"
        # For "both" mode, gpu_id is ignored but we still validate the range
        if v not in [0, 1]:
            raise ValueError("GPU ID must be 0 or 1")
        return v

class ModelConfig(BaseModel):
    """Configuration for a single model."""
    
    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    path: str = Field(..., description="Path to GGUF model file")
    gpu_config: Optional[GpuConfig] = Field(default=None, description="GPU configuration (optional)")
    parameters: ModelParameters = Field(default_factory=ModelParameters, description="Inference parameters")
    metadata: ModelMetadata = Field(default_factory=ModelMetadata, description="Model metadata")
    
    @field_validator("path")
    @classmethod
    def validate_model_path(cls, v: str) -> str:
        """Validate that model file exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Model file not found at: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        if not path.suffix.lower() in [".gguf", ".bin"]:
            raise ValueError(f"Invalid model file format. Expected .gguf or .bin, got: {path.suffix}")
        return v
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate model ID format."""
        if not v or not v.strip():
            raise ValueError("Model ID cannot be empty")
        # Allow alphanumeric, hyphens, and underscores
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("Model ID can only contain alphanumeric characters, hyphens, and underscores")
        return v

class ModelsConfig(BaseModel):
    """Configuration for all models."""
    
    models: List[ModelConfig] = Field(default_factory=list, description="List of configured models")
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID."""
        for model in self.models:
            if model.id == model_id:
                return model
        return None
    
    def get_model_ids(self) -> List[str]:
        """Get list of all model IDs."""
        return [model.id for model in self.models]
    
    @field_validator("models")
    @classmethod
    def validate_unique_ids(cls, v: List[ModelConfig]) -> List[ModelConfig]:
        """Validate that all model IDs are unique."""
        ids = [model.id for model in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate model IDs found: {set(duplicates)}")
        return v

class AuthUser(BaseModel):
    """User configuration for authentication."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password (will be hashed)")
    role: str = Field(default="user", description="User role")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username."""
        if not v or len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.isalnum():
            raise ValueError("Username can only contain alphanumeric characters")
        return v

class AuthConfig(BaseModel):
    """Configuration for authentication."""
    
    session_timeout: int = Field(default=3600, ge=60, description="Session timeout in seconds")
    max_login_attempts: int = Field(default=5, ge=1, description="Max failed login attempts")
    lockout_duration: int = Field(default=300, ge=0, description="Lockout duration in seconds")
    users: List[AuthUser] = Field(default_factory=list, description="Configured users")
    
    def get_user(self, username: str) -> Optional[AuthUser]:
        """Get user by username."""
        for user in self.users:
            if user.username == username:
                return user
        return None

class AppConfig(BaseModel):
    """Main application configuration combining all configs."""
    
    llama_cpp: LlamaCppConfig
    models: ModelsConfig
    auth: AuthConfig
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
