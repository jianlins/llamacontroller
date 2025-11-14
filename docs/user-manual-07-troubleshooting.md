# 7. Troubleshooting

This section lists common issues and solutions for LlamaController.

## Configuration Errors

- **Symptom:** Controller fails to start
- **Solution:** Check paths in `llamacpp-config.yaml` and `models-config.yaml`. Ensure files exist and paths are correct.

## Model Loading Failure

- **Symptom:** Model does not load or status remains "stopped"
- **Solution:** Verify model file path and GPU selection. Check available VRAM and compatibility.

## Port Conflicts

- **Symptom:** Error about port already in use
- **Solution:** Change port in configuration or stop conflicting process. Default ports: 8081 (GPU 0), 8088 (GPU 1).

## Permission Issues

- **Symptom:** Permission denied when starting llama.cpp
- **Solution:** Ensure executable permissions for llama-server binary.

## GPU Errors

- **Symptom:** Model fails to load on selected GPU
- **Solution:** Confirm CUDA drivers and llama.cpp CUDA support. Check GPU availability and memory.

## API Authentication Failure

- **Symptom:** API requests return "Unauthorized"
- **Solution:** Use a valid token in the `Authorization` header. Manage tokens in the Web UI.

## Log Analysis

- **Symptom:** Unknown error or unexpected behavior
- **Solution:** Check logs in the Web UI for detailed error messages.

## Other Issues

- **Symptom:** Web UI not accessible
- **Solution:** Ensure controller is running and listening on the correct port.

- **Symptom:** Session timeout or login issues
- **Solution:** Adjust session settings in `auth-config.yaml`.

---
