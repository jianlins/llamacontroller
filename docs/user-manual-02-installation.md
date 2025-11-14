# 2. Installation & Setup

## System Requirements

- Windows, Linux, or macOS
- Python 3.8+ (recommended: Conda/Miniconda)
- Git
- llama.cpp binaries (with CUDA support for GPU features)
- Sufficient GPU memory (for multi-GPU features)

## Step 1: Prepare Environment

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution).
2. Create and activate a new environment:
   ```bash
   conda create -n llama.cpp python=3.11 -y
   conda activate llama.cpp
   ```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Download llama.cpp and Models

- Place llama.cpp binaries in:  
  `C:\Users\VHASLCShiJ\software\llamacpp` (Windows)  
  `/path/to/llama.cpp` (Linux/macOS)
- Place GGUF model files in:  
  `C:\Users\VHASLCShiJ\software\ggufmodels`

## Step 4: Prepare Configuration Files

Create the following files in the `config/` directory:

- `llamacpp-config.yaml`: llama.cpp binary and port settings
- `models-config.yaml`: Model definitions and parameters
- `auth-config.yaml`: Authentication settings

Refer to example configs in the design documents.

## Step 5: Set Environment Variables (Optional)

```bash
# Windows (PowerShell)
$env:LLAMACPP_PATH = "C:\Users\VHASLCShiJ\software\llamacpp\llama-server.exe"
$env:MODELS_PATH = "C:\Users\VHASLCShiJ\software\ggufmodels"
$env:LLAMACONTROLLER_CONFIG = ".\config"
```

## Step 6: Project Structure

```
llamacontroller/
├── config/
├── src/
├── tests/
├── docs/
├── logs/
├── data/
```

## Step 7: Initial Verification

- Test llama.cpp binary:
  ```bash
  cd C:\Users\VHASLCShiJ\software\llamacpp
  .\llama-server.exe --help
  ```
- List available models:
  ```bash
  Get-ChildItem -Path "C:\Users\VHASLCShiJ\software\ggufmodels" -Filter "*.gguf"
  ```
- Start the controller and verify API/UI access.

## Troubleshooting

- Check paths and permissions if errors occur.
- Ensure required ports are available.
- Update configuration files as needed.

---
