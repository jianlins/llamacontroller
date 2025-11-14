# Development Setup Instructions

## Local Development Environment

This document provides setup instructions for developing and testing LlamaController on your local machine.

## Prerequisites

- **Python 3.8+** (via Conda environment)
- **Conda/Miniconda** installed
- Git
- Text editor or IDE (VS Code recommended)
- Terminal/Command prompt with PowerShell

## Conda Environment Setup

Create a dedicated conda environment for development:

```powershell
# Create new conda environment
conda create -n llama.cpp python=3.11 -y

# Activate the environment
conda activate llama.cpp

# Install required packages (to be determined during implementation)
# Examples:
# pip install fastapi uvicorn pyyaml bcrypt pyjwt
```

**Note**: Always activate the `llama.cpp` conda environment before running or developing LlamaController.

## Local Test Environment Configuration

### Test System Specifications

The following paths are configured for local development and testing:

#### llama.cpp Installation
- **Location**: `C:\Users\NLPDev\software\llamacpp`
- **Contents**: 
  - llama-server.exe (or llama-server)
  - llama-cli.exe (or llama-cli)
  - Other llama.cpp binaries and dependencies

#### Model Repository
- **Location**: `C:\Users\NLPDev\software\ggufmodels`
- **Contents**: GGUF model files for testing
- **Available Models**: 
  - `Phi-4-reasoning-plus-UD-IQ1_M.gguf` (3.57 GB)
  - `Qwen3-Coder-30B-A3B-Instruct-UD-TQ1_0.gguf` (7.46 GB)

### Initial Configuration Files

When testing, create the following configuration files:

#### 1. llama.cpp Configuration (`config/llamacpp-config.yaml`)

\\\yaml
llama_cpp:
  executable_path: "C:\\Users\\NLPDev\\software\\llamacpp\\llama-server.exe"
  default_host: "127.0.0.1"
  default_port: 8080
  log_level: "info"
  restart_on_crash: true
  max_restart_attempts: 3
  timeout_seconds: 300
\\\

**Note for cross-platform**: On Linux/macOS, adjust path to:
\\\yaml
executable_path: "/path/to/llama.cpp/llama-server"
\\\

#### 2. Model Configuration (`config/models-config.yaml`)

\\\yaml
models:
  - id: "phi-4-reasoning"
    name: "Phi-4 Reasoning Plus"
    path: "C:\\Users\\NLPDev\\software\\ggufmodels\\Phi-4-reasoning-plus-UD-IQ1_M.gguf"
    parameters:
      n_ctx: 16384  # Phi-4 supports long context
      n_gpu_layers: 33  # Adjust based on your GPU (0 for CPU-only)
      n_threads: 8
      temperature: 0.7
      top_p: 0.9
    metadata:
      description: "Phi-4 reasoning model with IQ1_M quantization"
      parameter_count: "14B"
      quantization: "IQ1_M"
      family: "phi"
      capabilities: ["completion", "chat", "reasoning"]
      
  - id: "qwen3-coder-30b"
    name: "Qwen3 Coder 30B Instruct"
    path: "C:\\Users\\NLPDev\\software\\ggufmodels\\Qwen3-Coder-30B-A3B-Instruct-UD-TQ1_0.gguf"
    parameters:
      n_ctx: 8192  # Qwen supports long context
      n_gpu_layers: 0  # Large model - adjust based on VRAM
      n_threads: 8
      temperature: 0.8
      top_p: 0.95
    metadata:
      description: "Qwen3 Coder 30B specialized for code generation"
      parameter_count: "30B"
      quantization: "TQ1_0"
      family: "qwen"
      capabilities: ["completion", "chat", "code"]
\\\

#### 3. Authentication Configuration (`config/auth-config.yaml`)

\\\yaml
authentication:
  session_timeout: 3600
  max_login_attempts: 5
  lockout_duration: 300
  
  # Development credentials (change in production!)
  users:
    - username: "admin"
      password: "admin123"  # Will be hashed on first run
      role: "admin"
\\\

**Security Warning**: These are development credentials. Change them before any production deployment.

## Verification Steps

### Step 1: Verify llama.cpp Installation

\\\powershell
# Test if llama-server exists and is executable
C:\Users\NLPDev\software\llamacpp\llama-server.exe --version
\\\

Expected output: Version information from llama.cpp

### Step 2: Verify Model Files

\\\powershell
# List all GGUF files
Get-ChildItem -Path "C:\Users\NLPDev\software\ggufmodels" -Filter "*.gguf"
\\\

Expected output: List of .gguf model files

### Step 3: Test Manual Model Loading (Optional)

\\\powershell
# Manually test loading a model with llama-server
cd C:\Users\NLPDev\software\llamacpp
.\llama-server.exe -m "C:\Users\NLPDev\software\ggufmodels\your-model.gguf" --port 8080
\\\

Then in another terminal:
\\\powershell
# Test with a simple request
curl http://localhost:8080/health
\\\

Press Ctrl+C to stop the server when done testing.

## Project Structure

Create the following directory structure for development:

\\\
llamacontroller/
├── design/                  # Design documents (this folder)
├── config/                  # Configuration files (create this)
│   ├── llamacpp-config.yaml
│   ├── models-config.yaml
│   └── auth-config.yaml
├── src/                     # Source code (to be created)
├── tests/                   # Test files (to be created)
├── docs/                    # Additional documentation (to be created)
├── logs/                    # Application logs (auto-created)
└── data/                    # Runtime data (tokens, sessions)
\\\

## Quick Start Commands

\\\powershell
# Create necessary directories
New-Item -ItemType Directory -Path "config", "logs", "data" -Force

# Copy example configurations (after they're created)
# ... development setup commands will be added after implementation ...
\\\

## Environment Variables (Optional)

For enhanced flexibility, you can use environment variables:

\\\powershell
# PowerShell
$env:LLAMACPP_PATH = "C:\Users\NLPDev\software\llamacpp\llama-server.exe"
$env:MODELS_PATH = "C:\Users\NLPDev\software\ggufmodels"
$env:LLAMACONTROLLER_CONFIG = ".\config"
\\\

## Troubleshooting

### Common Issues

**Issue**: llama-server not found
- **Solution**: Verify the path in `llamacpp-config.yaml` is correct and the file exists

**Issue**: Model file not found
- **Solution**: Check model paths in `models-config.yaml` use correct Windows path format with escaped backslashes

**Issue**: Permission denied
- **Solution**: Ensure llama-server.exe has execute permissions

**Issue**: Port already in use
- **Solution**: Change the port in `llamacpp-config.yaml` or stop the process using port 8080

### Checking Ports

\\\powershell
# Check if port 8080 is in use
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
\\\

## Getting Model Information

To understand what parameters to use for your models:

\\\powershell
# Use llama.cpp tools to inspect model
cd C:\Users\NLPDev\software\llamacpp
.\llama-cli.exe -m "C:\Users\NLPDev\software\ggufmodels\your-model.gguf" --help
\\\

## Next Steps

1. ✅ Verify llama.cpp installation
2. ✅ List available models
3. ✅ Create configuration files with actual model names
4. ⏳ Wait for implementation to begin development
5. ⏳ Run initial tests with local setup

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-11  
**Status**: Ready for Development
