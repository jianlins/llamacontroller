"""
llama.cpp process adapter for managing llama-server subprocess.
"""

import os
import subprocess
import threading
import time
import logging
import signal
import httpx
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from collections import deque

from ..models.config import LlamaCppConfig, ModelParameters
from ..models.lifecycle import ProcessStatus

logger = logging.getLogger(__name__)

class AdapterError(Exception):
    """Exception raised for adapter errors."""
    pass

class LlamaCppAdapter:
    """
    Manages llama-server subprocess lifecycle.
    
    Handles starting, stopping, monitoring, and communicating with
    the llama-server process.
    """
    
    def __init__(self, config: LlamaCppConfig):
        """
        Initialize the adapter.
        
        Args:
            config: llama.cpp configuration
        """
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.status = ProcessStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.restart_count = 0
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        self.log_buffer: deque = deque(maxlen=300)  # Keep last 300 log lines
        self._lock = threading.Lock()
        
        # HTTP client for health checks and proxying
        self.http_client: Optional[httpx.AsyncClient] = None
        
        logger.info("LlamaCppAdapter initialized")
    
    def start_server(
        self,
        model_path: str,
        params: ModelParameters,
        host: Optional[str] = None,
        port: Optional[int] = None,
        gpu_id: Optional[Union[int, str]] = None
    ) -> bool:
        """
        Start llama-server with specified model and parameters.
        
        Args:
            model_path: Path to GGUF model file
            params: Model inference parameters
            host: Host to bind to (default from config)
            port: Port to bind to (default from config)
            gpu_id: GPU identifier (0, 1, or "both") for CUDA_VISIBLE_DEVICES
            
        Returns:
            True if started successfully, False otherwise
            
        Raises:
            AdapterError: If server is already running or fails to start
        """
        with self._lock:
            if self.status not in [ProcessStatus.STOPPED, ProcessStatus.CRASHED]:
                raise AdapterError(f"Cannot start server: current status is {self.status}")
            
            self.status = ProcessStatus.STARTING
        
        try:
            # Validate model path
            if not Path(model_path).exists():
                raise AdapterError(f"Model file not found: {model_path}")
            
            # Build command line arguments
            host = host or self.config.default_host
            port = port or self.config.default_port
            
            # Build base command
            cmd = [
                self.config.executable_path,
                "-m", model_path,
                "--host", host,
                "--port", str(port),
            ]
            
            # Add API key if configured (for internal authentication)
            if self.config.api_key:
                cmd.extend(["--api-key", self.config.api_key])
                logger.info("llama-server will use API key authentication")
            
            # Add all parameters using the new flexible system
            model_params = params.get_cli_arguments()
            cmd.extend(model_params)
            
            # Log detailed parameter information
            logger.info(f"Model parameters from config:")
            logger.info(f"  - cli_params: {params.cli_params}")
            if params.n_ctx:
                logger.info(f"  - n_ctx (deprecated): {params.n_ctx}")
            if params.n_gpu_layers:
                logger.info(f"  - n_gpu_layers (deprecated): {params.n_gpu_layers}")
            if params.n_threads:
                logger.info(f"  - n_threads (deprecated): {params.n_threads}")
            logger.info(f"Converted to CLI arguments: {model_params}")
            
            # Set up environment variables for GPU selection
            env = None
            if gpu_id is not None:
                env = dict(os.environ)  # Copy current environment
                
                # Normalize gpu_id to string format
                if isinstance(gpu_id, int):
                    gpu_id_str = str(gpu_id)
                else:
                    gpu_id_str = str(gpu_id)
                
                # Handle legacy "both" format
                if gpu_id_str == "both":
                    logger.warning("gpu_id='both' is deprecated, use '0,1' instead")
                    gpu_id_str = "0,1"
                
                # Set CUDA_VISIBLE_DEVICES directly from gpu_id string
                env['CUDA_VISIBLE_DEVICES'] = gpu_id_str
                logger.info(f"Setting CUDA_VISIBLE_DEVICES={gpu_id_str}")
            
            # Log the exact command being executed
            logger.info(f"Starting llama-server: {' '.join(cmd)}")
            if env and 'CUDA_VISIBLE_DEVICES' in env:
                logger.info(f"Environment: CUDA_VISIBLE_DEVICES={env['CUDA_VISIBLE_DEVICES']}")
            logger.info(f"Full command: {' '.join(cmd)}")
            logger.info(f"Command as list: {cmd}")
            
            # Start the process with environment variables
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                encoding='utf-8',
                errors='replace',
                env=env  # Pass environment variables
            )
            
            self.start_time = datetime.now()
            
            # Start monitoring thread
            self.stop_monitoring.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True
            )
            self.monitor_thread.start()
            
            # Initialize HTTP client
            self.http_client = httpx.AsyncClient(
                base_url=f"http://{host}:{port}",
                timeout=30.0
            )
            
            with self._lock:
                self.status = ProcessStatus.RUNNING
            
            logger.info(f"llama-server started with PID {self.process.pid}")
            return True
            
        except Exception as e:
            with self._lock:
                self.status = ProcessStatus.ERROR
            logger.error(f"Failed to start llama-server: {e}")
            raise AdapterError(f"Failed to start server: {e}")
    
    def stop_server(self, graceful: bool = True, timeout: int = 30) -> bool:
        """
        Stop the llama-server process.
        
        Args:
            graceful: If True, try graceful shutdown first (SIGTERM)
            timeout: Timeout in seconds for graceful shutdown
            
        Returns:
            True if stopped successfully, False otherwise
        """
        with self._lock:
            if self.status == ProcessStatus.STOPPED:
                logger.info("Server already stopped")
                return True
            
            self.status = ProcessStatus.STOPPING
        
        try:
            if self.process is None:
                logger.warning("No process to stop")
                return True
            
            logger.info(f"Stopping llama-server (PID {self.process.pid})")
            
            if graceful:
                # Try graceful shutdown
                try:
                    self.process.terminate()  # SIGTERM
                    logger.info(f"Sent SIGTERM to process {self.process.pid}")
                    
                    # Wait for process to exit
                    try:
                        self.process.wait(timeout=timeout)
                        logger.info("Process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Process did not terminate within {timeout}s, forcing kill")
                        self.process.kill()  # SIGKILL
                        self.process.wait(timeout=5)
                        logger.info("Process killed forcefully")
                except Exception as e:
                    logger.error(f"Error during graceful shutdown: {e}")
                    self.process.kill()
                    self.process.wait(timeout=5)
            else:
                # Force kill
                self.process.kill()
                self.process.wait(timeout=5)
                logger.info("Process killed")
            
            # Stop monitoring thread
            self.stop_monitoring.set()
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            # Close HTTP client
            if self.http_client:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.http_client.aclose())
                    else:
                        asyncio.run(self.http_client.aclose())
                except Exception as e:
                    logger.warning(f"Error closing HTTP client: {e}")
                self.http_client = None
            
            self.process = None
            self.start_time = None
            
            with self._lock:
                self.status = ProcessStatus.STOPPED
            
            logger.info("llama-server stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            with self._lock:
                self.status = ProcessStatus.ERROR
            return False
    
    def restart_server(self) -> bool:
        """
        Restart the llama-server process.
        
        Returns:
            True if restarted successfully, False otherwise
        """
        logger.info("Restarting llama-server")
        
        # Store current configuration for restart
        # Note: This is a simplified version. In practice, you'd want to
        # store the model path and parameters when starting the server.
        
        if not self.stop_server():
            logger.error("Failed to stop server for restart")
            return False
        
        time.sleep(1)  # Brief pause before restart
        
        # Increment restart count
        self.restart_count += 1
        
        if self.restart_count > self.config.max_restart_attempts:
            logger.error(f"Max restart attempts ({self.config.max_restart_attempts}) exceeded")
            with self._lock:
                self.status = ProcessStatus.ERROR
            return False
        
        # Note: Actual restart would require stored model path and params
        logger.warning("Restart requires model path and parameters - not implemented in this version")
        return False
    
    async def is_healthy(self) -> bool:
        """
        Check if llama-server is healthy and responding.
        
        Returns:
            True if healthy, False otherwise
        """
        if self.status != ProcessStatus.RUNNING:
            return False
        
        if self.process is None or self.process.poll() is not None:
            return False
        
        # Try to connect to health endpoint
        if self.http_client:
            try:
                response = await self.http_client.get("/health", timeout=5.0)
                if response.status_code == 200:
                    return True
                logger.debug(f"Health check returned status {response.status_code}")
                return False
            except httpx.ConnectError as e:
                # Connection refused - server not ready yet
                logger.debug(f"Health check connection failed (server may still be starting): {e}")
                return False
            except httpx.TimeoutException as e:
                # Timeout - server may be loading model
                logger.debug(f"Health check timeout (server may be loading model): {e}")
                return False
            except Exception as e:
                logger.debug(f"Health check failed: {e}")
                return False
        
        return False
    
    def get_status(self) -> ProcessStatus:
        """Get current process status."""
        with self._lock:
            return self.status
    
    def get_pid(self) -> Optional[int]:
        """Get process ID if running."""
        if self.process:
            return self.process.pid
        return None
    
    def get_uptime_seconds(self) -> Optional[int]:
        """Get uptime in seconds."""
        if self.start_time and self.status == ProcessStatus.RUNNING:
            return int((datetime.now() - self.start_time).total_seconds())
        return None
    
    async def proxy_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False
    ) -> httpx.Response:
        """
        Proxy HTTP request to llama-server.
        
        Args:
            endpoint: API endpoint (e.g., "/v1/chat/completions")
            method: HTTP method
            data: Request body (for POST/PUT)
            headers: Additional headers
            stream: Whether to stream the response
            
        Returns:
            HTTP response from llama-server
            
        Raises:
            AdapterError: If server is not running or request fails
        """
        if self.status != ProcessStatus.RUNNING:
            raise AdapterError(f"Cannot proxy request: server status is {self.status}")
        
        if not self.http_client:
            raise AdapterError("HTTP client not initialized")
        
        try:
            request_kwargs = {
                "url": endpoint,
                "headers": headers or {},
            }
            
            if data:
                request_kwargs["json"] = data
            
            if method.upper() == "GET":
                response = await self.http_client.get(**request_kwargs)
            elif method.upper() == "POST":
                response = await self.http_client.post(**request_kwargs)
            elif method.upper() == "PUT":
                response = await self.http_client.put(**request_kwargs)
            elif method.upper() == "DELETE":
                response = await self.http_client.delete(**request_kwargs)
            else:
                raise AdapterError(f"Unsupported HTTP method: {method}")
            
            return response
            
        except httpx.RequestError as e:
            logger.error(f"Request to llama-server failed: {e}")
            raise AdapterError(f"Request failed: {e}")
    
    def get_logs(self, lines: int = 100) -> List[str]:
        """
        Get recent log lines from llama-server.
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of log lines
        """
        with self._lock:
            return list(self.log_buffer)[-lines:]
    
    def _monitor_process(self) -> None:
        """
        Monitor llama-server process in background thread.
        
        Captures stdout/stderr and detects crashes.
        """
        logger.info("Process monitoring started")
        
        try:
            while not self.stop_monitoring.is_set():
                if self.process is None:
                    break
                
                # Check if process is still alive
                poll_result = self.process.poll()
                if poll_result is not None:
                    # Process has exited - read all remaining output
                    logger.error(f"llama-server process exited with code {poll_result}")
                    
                    # Read any remaining output
                    if self.process.stdout:
                        try:
                            remaining_output = self.process.stdout.read()
                            if remaining_output:
                                for line in remaining_output.split('\n'):
                                    line = line.strip()
                                    if line:
                                        self.log_buffer.append(line)
                                        logger.error(f"llama-server: {line}")
                        except Exception as e:
                            logger.warning(f"Error reading remaining output: {e}")
                    
                    with self._lock:
                        self.status = ProcessStatus.CRASHED
                    
                    # Handle crash if auto-restart is enabled
                    if self.config.restart_on_crash:
                        self._handle_crash()
                    
                    break
                
                # Read output (non-blocking)
                if self.process.stdout:
                    try:
                        line = self.process.stdout.readline()
                        if line:
                            line = line.strip()
                            self.log_buffer.append(line)
                            logger.debug(f"llama-server: {line}")
                    except Exception as e:
                        logger.warning(f"Error reading process output: {e}")
                
                time.sleep(0.1)  # Small delay to avoid busy waiting
                
        except Exception as e:
            logger.error(f"Error in process monitoring: {e}")
        finally:
            logger.info("Process monitoring stopped")
    
    def _handle_crash(self) -> None:
        """Handle process crash and attempt restart if configured."""
        logger.warning("Handling llama-server crash")
        
        if self.restart_count >= self.config.max_restart_attempts:
            logger.error(f"Max restart attempts reached, giving up")
            with self._lock:
                self.status = ProcessStatus.ERROR
            return
        
        # Wait before restart (exponential backoff)
        wait_time = min(2 ** self.restart_count, 60)
        logger.info(f"Waiting {wait_time}s before restart attempt {self.restart_count + 1}")
        time.sleep(wait_time)
        
        # Attempt restart
        # Note: This would require storing model path and params
        logger.warning("Auto-restart not fully implemented - requires stored configuration")
    
    def __del__(self):
        """Cleanup when adapter is destroyed."""
        if self.process and self.process.poll() is None:
            logger.warning("Adapter being destroyed with running process, stopping it")
            self.stop_server(graceful=False, timeout=5)
