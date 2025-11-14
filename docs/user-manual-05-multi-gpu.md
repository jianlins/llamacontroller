# 5. Multi-GPU Features

LlamaController supports loading models on multiple GPUs, allowing different models to run on separate GPUs or split across several GPUs.

## Overview

- Select GPU(s) when loading a model via Web UI or API
- Each GPU runs a separate llama.cpp instance on a dedicated port
- Supports combinations like GPU 0, GPU 1, or both (e.g., "0", "1", "0,1")

## Configuration

- Update `models-config.yaml` to specify GPU selection:
  ```yaml
  gpu_config:
    mode: "single"  # "single" or "both"
    gpu_id: 0       # 0, 1, or "0,1"
  ```
- Port mapping (default):
  - GPU 0: 8081
  - GPU 1: 8088
  - Both: 8081

## Web UI Usage

- On the Dashboard, select one or more GPUs using toggle buttons or checkboxes
- The UI displays current GPU assignments and model status

## API Usage

- Specify `gpu_id` when loading a model:
  ```json
  {
    "model_id": "phi-4-reasoning",
    "gpu_id": "0"      // GPU 0 only
  }
  ```
  ```json
  {
    "model_id": "qwen3-coder-30b",
    "gpu_id": "1"      // GPU 1 only
  }
  ```
  ```json
  {
    "model_id": "large-model",
    "gpu_id": "0,1"    // Both GPUs
  }
  ```

## Model Status Display

- Dashboard shows which GPU is running which model, port number, memory usage, and status

## Limitations

- Requires at least 2 NVIDIA GPUs with sufficient VRAM
- llama.cpp must support CUDA and tensor-split parameter
- Ports 8081 and 8088 must be available
- Only one model per GPU at a time

## Troubleshooting

- If a GPU is busy, loading another model will fail
- Check logs and Dashboard for error messages
- Ensure correct configuration and hardware

---
