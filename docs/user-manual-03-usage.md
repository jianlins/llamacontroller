# 3. Basic Usage

## Starting LlamaController

1. Activate your Conda environment:
   ```bash
   conda activate llama.cpp
   ```
2. Start the controller:
   ```bash
   python run.py
   ```
3. Access the Web UI in your browser:
   ```
   http://localhost:3000
   ```

## Logging In

- Use your configured username and password (see `auth-config.yaml`).
- Default credentials for development:
  - Username: `admin`
  - Password: `admin123`

## Loading a Model

1. Go to the Dashboard in the Web UI.
2. Select a model from the list.
3. Choose GPU(s) if multi-GPU is enabled.
4. Click "Load Model".
5. Wait for status to show "Running".

## Unloading or Switching Models

- To unload: Click "Unload Model" next to the running model.
- To switch: Select a new model and click "Switch Model".

## API Usage (Quick Example)

- Use Ollama-compatible endpoints for integration.
- Example: Generate completion via API
  ```bash
  curl -X POST http://localhost:3000/api/generate \
    -H "Authorization: Bearer <your_token>" \
    -d '{"model": "phi-4-reasoning", "prompt": "Hello"}'
  ```

## Configuration Overview

- `llamacpp-config.yaml`: llama.cpp binary and port settings
- `models-config.yaml`: Model definitions and parameters
- `auth-config.yaml`: User authentication

## Common Operations

- View model status and resource usage in Dashboard.
- Manage API tokens in the Web UI.
- Check logs for troubleshooting.

---
