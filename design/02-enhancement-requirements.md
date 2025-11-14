# Enhancement Requirements

## Document Information
- **Version**: 1.0
- **Last Updated**: 2025-11-12
- **Status**: Requirements Specification
- **Category**: Feature Enhancements

## Overview

This document specifies new enhancement requirements for the LlamaController project that extend the initial design with additional functionality for API access control and multi-GPU support.

---

## Requirement 1: API UI Access with Authentication

### Summary
Add a navigation link from the Controller UI to the llama.cpp API UI page (Swagger/OpenAPI interface), with access requiring authentication.

### Current State
- LlamaController has a web-based management UI with authentication
- llama.cpp server runs on localhost:8080 (or configured port)
- llama.cpp provides a built-in Swagger UI at its base URL
- Currently, the llama.cpp API UI is not integrated into LlamaController's navigation

### Required Changes

#### 1.1 Navigation Integration
**Requirement**: Add a navigation link in the LlamaController UI to access the llama.cpp API documentation/testing interface.

**Implementation Details**:
- Add "API Documentation" or "API UI" menu item in the navigation bar
- Link should be visible to authenticated users only
- Position in navigation: Between "Dashboard" and "Logs" (suggested)

**UI Location**: `src/llamacontroller/web/templates/base.html`

#### 1.2 Authenticated Proxy Endpoint
**Requirement**: Create a proxy endpoint that forwards requests to the llama.cpp Swagger UI while enforcing authentication.

**Implementation Details**:
- Create new route: `GET /api-ui` or `/swagger-ui`
- Require session-based authentication (same as other UI pages)
- Proxy/redirect to llama.cpp server's Swagger UI
- Preserve all Swagger UI functionality (interactive API testing)

**Technical Approaches**:

**Option A: Reverse Proxy (Recommended)**
```python
@router.get("/api-ui")
async def api_ui(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Proxy to llama.cpp Swagger UI with authentication."""
    # Proxy all requests to llama.cpp server
    # Maintain WebSocket connections for interactive features
    pass
```

**Option B: Embedded iFrame**
```python
@router.get("/api-ui")
async def api_ui(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Render page with embedded llama.cpp Swagger UI."""
    return templates.TemplateResponse("api_ui.html", {
        "request": request,
        "user": current_user,
        "llama_api_url": f"http://{llama_host}:{llama_port}"
    })
```

**Files to Modify**:
- `src/llamacontroller/web/routes.py` - Add new route
- `src/llamacontroller/web/templates/base.html` - Add navigation link
- `src/llamacontroller/web/templates/api_ui.html` - New template (if using iframe)

#### 1.3 Security Considerations
- Ensure llama.cpp server remains on localhost only (not exposed externally)
- All access to llama.cpp API UI must go through authenticated LlamaController
- Consider CORS configuration for iframe approach
- Maintain session timeout behavior

---

## Requirement 2: Multi-GPU Support with Port Management

### Summary
Enable users to select which GPU(s) to use for model loading, with support for loading different models on different GPUs using separate llama.cpp instances on different ports.

### Current State
- Single llama.cpp instance on default port (8080)
- Model configuration includes `n_gpu_layers` parameter (single value)
- No GPU selection UI or configuration
- No support for multiple simultaneous llama.cpp instances

### Required Changes

#### 2.1 GPU Selection Configuration

**Requirement**: Support GPU selection in model configuration with three options:
1. GPU 0 only
2. GPU 1 only  
3. Both GPUs

**Configuration Schema Update**:

```yaml
# config/models-config.yaml
models:
  - id: "phi-4-reasoning"
    name: "Phi-4 Reasoning Plus"
    path: "C:\\Users\\NLPDev\\software\\ggufmodels\\Phi-4-reasoning-plus-UD-IQ1_M.gguf"
    gpu_config:
      mode: "single"  # Options: "single", "both"
      gpu_id: 0       # For single mode: 0 or 1; ignored for both mode
    parameters:
      n_ctx: 16384
      n_gpu_layers: 33
      n_threads: 8
    # ... rest of config
```

**UI Requirements**:
- Add GPU selection controls in the Dashboard when loading a model
- Display options: "GPU 0", "GPU 1", "Both GPUs"
- Show current GPU assignment for loaded models
- Validate that different models on different GPUs use compatible settings

#### 2.2 Port Assignment Strategy

**Requirement**: Assign different ports to llama.cpp instances based on GPU assignment.

**Port Mapping**:
- **GPU 0**: Port 8081 (default)
- **GPU 1**: Port 8088
- **Both GPUs**: Port 8081 (primary) - uses default GPU 0 port

**Configuration Update**:

```yaml
# config/llamacpp-config.yaml
llama_cpp:
  executable_path: "C:\\Users\\NLPDev\\software\\llamacpp\\llama-server.exe"
  default_host: "127.0.0.1"
  gpu_ports:
    gpu0: 8081
    gpu1: 8088
    both: 8081  # Uses GPU 0 port when both GPUs are used
  log_level: "info"
  restart_on_crash: true
  max_restart_attempts: 3
  timeout_seconds: 300
```

**Implementation Notes**:
- Each GPU gets its own llama.cpp server instance
- Multiple instances can run simultaneously
- Port assignment is automatic based on GPU selection
- Both GPUs mode runs single instance with multi-GPU support

#### 2.3 Multi-Instance Process Management

**Requirement**: Manage multiple llama.cpp server processes simultaneously.

**Process Tracking Data Structure**:

```python
# In ModelLifecycleManager
class GpuInstance:
    gpu_id: int | str  # 0, 1, or "both"
    port: int
    process: subprocess.Popen
    model_id: str
    status: InstanceStatus

gpu_instances: Dict[int | str, GpuInstance] = {}
```

**Key Operations**:

1. **Load Model on Specific GPU**:
   ```python
   async def load_model(model_id: str, gpu_id: int | str) -> ModelStatus:
       # Determine port from gpu_id
       port = get_port_for_gpu(gpu_id)
       # Start llama-server with GPU-specific parameters
       # Track instance in gpu_instances dict
   ```

2. **Unload Model from GPU**:
   ```python
   async def unload_model(gpu_id: int | str) -> None:
       # Stop specific llama-server instance
       # Remove from gpu_instances dict
   ```

3. **Get Status by GPU**:
   ```python
   async def get_gpu_status(gpu_id: int | str) -> GpuStatus:
       # Return status of specific GPU instance
   ```

4. **Get All GPU Statuses**:
   ```python
   async def get_all_gpu_statuses() -> Dict[str, GpuStatus]:
       # Return status of all GPU instances
   ```

#### 2.4 Model Status Display Enhancement

**Requirement**: Display which GPU is loading which model in the model status view.

**Status Information to Display**:
- GPU ID (0, 1, or "Both")
- Model name loaded on each GPU
- Port number for each instance
- Memory usage per GPU (if available)
- Status (running, stopped, error) per GPU

**UI Mockup**:
```
┌─────────────────────────────────────────────────────────┐
│ Model Status                                             │
├─────────────────────────────────────────────────────────┤
│ GPU 0 (Port 8081)                                        │
│   Model: Phi-4 Reasoning Plus                           │
│   Status: ● Running                                      │
│   Memory: 3.57 GB                                        │
│   [Unload Model]                                         │
├─────────────────────────────────────────────────────────┤
│ GPU 1 (Port 8088)                                        │
│   Model: Qwen3 Coder 30B                                │
│   Status: ● Running                                      │
│   Memory: 7.46 GB                                        │
│   [Unload Model]                                         │
└─────────────────────────────────────────────────────────┘
```

**Template Updates**:
- `src/llamacontroller/web/templates/partials/model_status.html` - Enhanced status display
- `src/llamacontroller/web/templates/dashboard.html` - GPU-aware controls

#### 2.5 API Request Routing

**Requirement**: Route API requests to the correct llama.cpp instance based on which GPU is handling the model.

**Routing Strategy**:

**Option A: Automatic Routing (Recommended)**
- Maintain a mapping: `model_id -> gpu_id -> port`
- When API request comes in, determine which GPU has the model loaded
- Route to appropriate port automatically

**Option B: Explicit GPU Selection in API**
- Require API clients to specify GPU in request headers or parameters
- Route based on explicit specification

**Implementation (Option A)**:
```python
async def route_request_to_model(model_id: str, request_data: dict):
    # Look up which GPU has this model
    gpu_id = get_gpu_for_model(model_id)
    if gpu_id is None:
        raise ModelNotLoadedError(f"Model {model_id} is not loaded")
    
    # Get port for this GPU
    port = get_port_for_gpu(gpu_id)
    
    # Proxy request to correct llama.cpp instance
    return await proxy_to_llama(port, request_data)
```

#### 2.6 llama.cpp Parameter Updates

**Requirement**: Pass GPU-specific parameters to llama.cpp when starting server.

**GPU 0 Only**:
```bash
llama-server.exe \
  --model <model_path> \
  --port 8081 \
  --gpu-layers 33 \
  --tensor-split 1,0  # All on GPU 0
```

**GPU 1 Only**:
```bash
llama-server.exe \
  --model <model_path> \
  --port 8088 \
  --gpu-layers 33 \
  --tensor-split 0,1  # All on GPU 1
```

**Both GPUs**:
```bash
llama-server.exe \
  --model <model_path> \
  --port 8081 \
  --gpu-layers 33 \
  --tensor-split 0.5,0.5  # Split across both GPUs
```

**Notes**:
- `--tensor-split` parameter controls GPU distribution
- May need to adjust based on llama.cpp version and GPU capabilities
- Verify parameter names with current llama.cpp documentation

---

## Implementation Priority

### Phase 1: API UI Access (Lower Complexity)
1. Add navigation link to base template
2. Create authenticated proxy/iframe route
3. Test access and authentication
4. Update user documentation

**Estimated Effort**: 2-4 hours

### Phase 2: Multi-GPU Support (Higher Complexity)
1. Update configuration schemas and models
2. Implement multi-instance process management
3. Add GPU selection UI controls
4. Update model status display
5. Implement request routing logic
6. Update llama.cpp adapter for GPU parameters
7. Comprehensive testing with multiple GPUs
8. Update documentation

**Estimated Effort**: 1-2 weeks

---

## Testing Requirements

### API UI Access Testing
- [ ] Verify navigation link appears for authenticated users
- [ ] Verify navigation link does not appear for unauthenticated users
- [ ] Test accessing API UI without authentication (should redirect to login)
- [ ] Test accessing API UI with valid session (should display Swagger UI)
- [ ] Test all Swagger UI interactive features work through proxy
- [ ] Verify session timeout behaves correctly on API UI page

### Multi-GPU Testing
- [ ] Test loading single model on GPU 0
- [ ] Test loading single model on GPU 1
- [ ] Test loading single model on both GPUs
- [ ] Test loading different models on GPU 0 and GPU 1 simultaneously
- [ ] Test unloading model from specific GPU
- [ ] Test model status display shows correct GPU assignments
- [ ] Test API requests route to correct GPU instance
- [ ] Test port conflicts (both GPUs should use same port strategy)
- [ ] Test system behavior when GPU is not available
- [ ] Test memory monitoring per GPU (if implemented)
- [ ] Verify llama.cpp parameters passed correctly for each GPU mode

---

## Dependencies and Constraints

### Hardware Requirements
- **Minimum**: System with 2 NVIDIA GPUs
- **GPU Memory**: Sufficient VRAM on each GPU for intended models
- **CUDA**: Compatible CUDA drivers installed

### Software Requirements
- llama.cpp compiled with CUDA support
- llama.cpp version supporting `--tensor-split` parameter
- NVIDIA drivers and CUDA toolkit

### Configuration Constraints
- Port 8081 and 8088 must be available
- llama.cpp must support simultaneous instances
- Sufficient system resources for multiple llama.cpp processes

---

## Future Considerations

### Potential Enhancements
1. **Dynamic Port Assignment**: Auto-select available ports instead of fixed mapping
2. **GPU Auto-Selection**: Automatically choose GPU based on current load
3. **Load Balancing**: Distribute requests across GPUs for same model
4. **GPU Memory Monitoring**: Real-time VRAM usage display
5. **Multi-Model per GPU**: Support multiple models on single GPU
6. **GPU Affinity Settings**: Fine-tune GPU placement strategies
7. **Fallback Strategies**: Automatic failover if GPU becomes unavailable

### Scalability Notes
- Current design supports 2 GPUs (as specified in requirements)
- Architecture allows extension to N GPUs with minimal changes
- Port mapping strategy would need enhancement for >2 GPUs

---

## API Changes

### New Endpoints

#### Load Model with GPU Selection
```
POST /api/v1/models/load
{
  "model_id": "phi-4-reasoning",
  "gpu_id": 0  // 0, 1, or "both"
}
```

#### Get GPU Status
```
GET /api/v1/gpu/status
Response:
{
  "gpu0": {
    "model_id": "phi-4-reasoning",
    "port": 8081,
    "status": "running",
    "memory_used_mb": 3650
  },
  "gpu1": {
    "model_id": "qwen3-coder-30b",
    "port": 8088,
    "status": "running",
    "memory_used_mb": 7630
  }
}
```

#### Unload Model from GPU
```
POST /api/v1/models/unload
{
  "gpu_id": 0  // Unload from specific GPU
}
```

---

## Documentation Updates Required

### User-Facing Documentation
- [ ] Update QUICKSTART.md with GPU selection instructions
- [ ] Add API UI access guide
- [ ] Update configuration examples with GPU settings
- [ ] Add troubleshooting section for multi-GPU issues

### Developer Documentation
- [ ] Update architecture diagrams with multi-instance design
- [ ] Document GPU routing logic
- [ ] Add examples of llama.cpp parameter construction
- [ ] Update API documentation with new endpoints

---

## Success Criteria

### Requirement 1: API UI Access
- ✅ Navigation link visible to authenticated users
- ✅ API UI accessible only after authentication
- ✅ All Swagger UI features functional
- ✅ Session management consistent with rest of application

### Requirement 2: Multi-GPU Support
- ✅ Users can select GPU 0, GPU 1, or both when loading models
- ✅ Different models can run simultaneously on different GPUs
- ✅ Each GPU instance uses correct port (8081 for GPU 0, 8088 for GPU 1)
- ✅ Model status clearly shows which GPU is running which model
- ✅ API requests route correctly to appropriate GPU instance
- ✅ System stable with multiple concurrent models

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-12  
**Status**: Requirements Specification  
**Next Steps**: Review requirements, prioritize implementation, update architecture design
