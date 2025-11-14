# GPU Status Detection and Selection Design

## Refined User Requirements

This feature is intended for Windows OS with NVIDIA GPUs. The controller should use the `nvidia-smi` command to automatically detect the number of GPUs and the status of each GPU. If NVIDIA GPUs are not available, the system should default to CPU.

- The controller periodically queries the memory usage of each GPU.
- If a GPU's memory usage exceeds 30MB, it is considered "in use".
    - If the controller knows a model is loaded on this GPU, display the model's name.
    - If the GPU is occupied by other users or processes (i.e., no model loaded by the controller), display "Occupied by someone else" and disable the corresponding GPU selection button to prevent loading a model onto that GPU.
- Users can only select idle GPUs to load models; selection buttons for occupied GPUs are disabled.
- This feature is designed for multi-user environments to improve resource utilization and safety.

## Design Highlights

1. **GPU Detection Workflow**
    - Use `nvidia-smi --query-gpu=index,memory.used --format=csv,noheader` to get the memory usage of all GPUs.
    - If the command is unavailable or no GPUs are detected, automatically switch to CPU mode.

2. **Configurable Memory Threshold and Model Mapping**
    - The memory usage threshold for considering a GPU "occupied" is configurable (default: 30MB). This can be set via a configuration file or UI.
    - The controller maintains a mapping between GPUs and loaded models (using internal state or database).
    - If a model is loaded, display its name; otherwise, show "Occupied by someone else" and disable the selection button.

3. **Detailed Workflow and Logic Pseudocode**
    - Detection and status update process using nvidia-smi output (see `data/gpu.txt` for example):
      ```python
      # Pseudocode for GPU status detection with configurable threshold and process info
      memory_threshold = config.get("gpu_memory_threshold", 30)  # MB
      gpu_status_list = []
      gpu_info = parse_gpu_memory_usage("data/gpu.txt")  # e.g. [{'index': 0, 'memory_used': 1}, {'index': 1, 'memory_used': 363}]
      process_info = parse_gpu_processes("data/gpu.txt") # e.g. [{'gpu_index': 1, 'pid': 1234, 'process_name': 'python.exe', 'used_memory': 363}]
      for gpu in gpu_info:
          if gpu["memory_used"] > memory_threshold:
              if gpu["index"] in controller.loaded_models:
                  status = {
                      "index": gpu["index"],
                      "state": "model_loaded",
                      "model_name": controller.loaded_models[gpu["index"]],
                      "select_enabled": True
                  }
              else:
                  # Show process info if available, otherwise "Occupied by someone else"
                  proc = [p for p in process_info if p["gpu_index"] == gpu["index"]]
                  status = {
                      "index": gpu["index"],
                      "state": "occupied_by_others",
                      "model_name": None,
                      "process_info": proc if proc else None,
                      "select_enabled": False
                  }
          else:
              status = {
                  "index": gpu["index"],
                  "state": "idle",
                  "model_name": None,
                  "select_enabled": True
              }
          gpu_status_list.append(status)
      # If no GPU detected, fallback to CPU
      if not gpu_status_list:
          gpu_status_list = [{"index": "CPU", "state": "idle", "model_name": None, "select_enabled": True}]
      ```

    - **Example based on data/gpu.txt:**
      - GPU 0: 1MiB used (< threshold), status: idle, selectable.
      - GPU 1: 363MiB used (> threshold), no process listed, status: occupied by someone else, not selectable.

    - If process info is present, display PID and process name for each occupied GPU.

4. **UI and Integration Details**
    - Display a list of GPUs with their status (idle / model loaded / occupied by others).
    - Disable selection buttons for occupied GPUs.
    - Show model names for GPUs with loaded models.
    - For occupied GPUs, display process and (if available) user info for each process using the GPU.
    - **Automatic Status Refresh**: The Web UI automatically refreshes GPU status every 5 minutes using HTMX polling.
        - HTMX `hx-trigger="every 300s"` on the dashboard content div
        - Endpoint: `GET /dashboard/refresh` returns updated GPU status
        - Visual indicator shows "Auto-refresh: Active (5m)" badge in dashboard header
        - No page reload required - seamless updates
        - **Pre-load Refresh**: Before loading a model, the system automatically refreshes GPU status to ensure accurate occupancy detection
    - Integrate with Web UI via RESTful API for real-time updates.

5. **Model Load Protection**
    - **Pre-load GPU Status Check**: Before attempting to load a model on any GPU:
        - System refreshes GPU hardware status via `nvidia-smi`
        - Verifies selected GPU(s) are not occupied by external processes
        - Prevents model loading if GPU is occupied (memory usage > threshold)
        - Returns clear error message if GPU became occupied between selection and load
    - **Dynamic Button State During Model Operations**:
        - When a model is loaded on a GPU, that GPU's selection button is disabled for other models
        - Button shows visual indicator (⚡) that model is running on that GPU
        - Button remains disabled until the model is unloaded from that GPU
        - Multi-GPU scenarios (e.g., "0,1"): both GPUs are disabled when model uses them
        - On model unload, affected GPU buttons are immediately re-enabled (after status refresh)

6. **Dynamic UI Generation Requirements**
    - **GPU Count Display**: The UI must dynamically display the total number of available GPUs detected by the system.
        - Show a summary at the top of the GPU selection interface: e.g., "Total GPUs: 4" or "Total GPUs: 2".
        - If no NVIDIA GPUs are detected, display "CPU Mode (No GPU Detected)".
    - **Synchronized GPU Button Generation**: For each model in the model list, dynamically generate GPU selection buttons based on the actual number of detected GPUs.
        - If 2 GPUs are detected, generate 2 GPU buttons (GPU 0, GPU 1) for each model.
        - If 4 GPUs are detected, generate 4 GPU buttons (GPU 0, GPU 1, GPU 2, GPU 3) for each model.
        - If no GPU is detected, show a single "CPU" button for each model.
    - **Dynamic Button State Management**: Each GPU button should reflect the real-time status:
        - **Idle**: Button enabled, can be selected to load a model.
        - **Model Loaded (by this controller)**: Button shows the model name, enabled for unloading or management.
        - **Occupied by Others**: Button disabled with label "Occupied" or process info shown.
    - **Implementation Approach**:
        - Backend API should return:
            - Total GPU count: `total_gpus: int`
            - GPU status list with detailed state information for each GPU
        - Frontend (Web UI) should:
            - Fetch GPU count and status on page load and periodic refresh
            - Use template loops or JavaScript to dynamically generate GPU buttons for each model
            - Synchronize the number of buttons with the detected GPU count
        - **Example API Response**:
          ```json
          {
            "total_gpus": 4,
            "gpu_status": [
              {"index": 0, "state": "idle", "model_name": null, "select_enabled": true},
              {"index": 1, "state": "model_loaded", "model_name": "llama-7b", "select_enabled": true},
              {"index": 2, "state": "occupied_by_others", "model_name": null, "select_enabled": false, "process_info": [{"pid": 5678, "process_name": "python.exe"}]},
              {"index": 3, "state": "idle", "model_name": null, "select_enabled": true}
            ]
          }
          ```
        - **Frontend Template Example** (Pseudo-code):
          ```html
          <div class="gpu-summary">Total GPUs: {{ total_gpus }}</div>
          <div class="model-list">
            {% for model in models %}
              <div class="model-item">
                <h3>{{ model.name }}</h3>
                <div class="gpu-buttons">
                  {% for gpu in gpu_status %}
                    <button 
                      class="gpu-btn gpu-{{ gpu.index }}"
                      data-gpu="{{ gpu.index }}"
                      data-model="{{ model.name }}"
                      {% if not gpu.select_enabled %}disabled{% endif %}>
                      GPU {{ gpu.index }}
                      {% if gpu.model_name %}({{ gpu.model_name }}){% endif %}
                      {% if gpu.state == 'occupied_by_others' %}(Occupied){% endif %}
                    </button>
                  {% endfor %}
                </div>
              </div>
            {% endfor %}
          </div>
          ```

6. **Error Handling**
    - If `nvidia-smi` fails or no GPU is detected, notify the user and switch to CPU.

7. **Integration with Existing Architecture**
    - Encapsulate GPU status detection logic as an independent module for use by the controller and Web UI.
    - Store GPU-model mapping in controller state or database.
    - Recommend RESTful API or WebSocket for real-time GPU status updates in the Web UI.

## Reference Command

```shell
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
```

## Testing on Non-GPU Machines

- For development and testing on machines without NVIDIA GPUs, implement a mock mode:
    - Allow the controller to use a static output file (e.g., `data/gpu.txt`) or a configurable string as the simulated result of the `nvidia-smi` command.
    - Provide a configuration option or environment variable to enable/disable mock mode.
    - Ensure all GPU detection and parsing logic works identically with both real and mock data.

## Future Extensions

- Support more GPU types or cross-platform compatibility.
- Add configurable memory usage threshold.
- Enable automatic GPU status refresh.
