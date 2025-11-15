# LlamaController

[![Pytest](https://github.com/jianlins/llamacontroller/actions/workflows/test-collection.yml/badge.svg)](https://github.com/jianlins/llamacontroller/actions/workflows/test-collection.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](https://github.com/jianlins/llamacontroller)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

![项目截图](docs/image.png)

A WebUI-based management system for llama.cpp model lifecycle with Ollama API compatibility.

## 🎯 Project Overview

LlamaController provides a secure, web-based interface to manage llama.cpp instances with full model lifecycle control (load, unload, switch) while maintaining compatibility with Ollama's REST API ecosystem. This allows existing Ollama-compatible applications to seamlessly work with llama.cpp deployments.

## ✨ Features

- **Centralized Model Management**: Single interface to control multiple models
- **API Compatibility**: Drop-in replacement for Ollama in existing workflows
- **Configuration Isolation**: Separate llama.cpp binaries from model configurations
- **Secure Access**: Protected by authentication with token-based API access
- **Multi-tenancy Support**: Different tokens for different applications/users
- **Web Interface**: User-friendly dashboard for model management
- **Multi-GPU Support**: Load models on GPU 0, GPU 1, or both GPUs (in progress)
- **GPU Status Detection**: Real-time monitoring of GPU usage, supports idle/model-loaded/occupied-by-others states
- **Mock GPU Testing**: Supports mock mode for GPU status testing on machines without NVIDIA GPU
- **Automatic GPU Status Refresh**: Optimized refresh interval (5min), manual refresh on model load/unload
- **Air-Gap Support**: All web and API resources are served locally, fully offline compatible

## 📋 Prerequisites

- Python 3.8+ (Conda environment recommended)
- llama.cpp installed with `llama-server` executable
- GGUF model files
- Optional: Multiple NVIDIA GPUs for multi-GPU support

## 🚀 Quick Start

### 1. Set up Conda Environment

```powershell
conda create -n llama.cpp python=3.11 -y
conda activate llama.cpp
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Initialize Database

```powershell
python scripts/init_db.py
```

### 4. Configure

Edit the configuration files in `config/` directory to match your system:
- `config/llamacpp-config.yaml` - llama.cpp server settings
- `config/models-config.yaml` - Available models configuration
- `config/auth-config.yaml` - Authentication settings

### 5. Start LlamaController

```powershell
python run.py
```

### 6. Access Web UI

Open your browser and navigate to: `http://localhost:3000`

**Default credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Important**: Change the default password after first login!

## 📁 Project Structure

```
llamacontroller/
├── src/llamacontroller/       # Main application code
│   ├── core/                  # Core business logic
│   │   ├── config.py          # Configuration management
│   │   ├── lifecycle.py       # Model lifecycle manager
│   │   └── adapter.py         # llama.cpp process adapter
│   ├── api/                   # REST API endpoints
│   │   ├── management.py      # Management API
│   │   ├── ollama.py          # Ollama-compatible API
│   │   ├── auth.py            # Authentication endpoints
│   │   └── tokens.py          # Token management
│   ├── auth/                  # Authentication
│   │   ├── service.py         # Auth service
│   │   └── dependencies.py    # FastAPI auth dependencies
│   ├── db/                    # Database models
│   │   ├── models.py          # SQLAlchemy models
│   │   └── crud.py            # Database operations
│   ├── web/                   # Web UI
│   │   ├── routes.py          # Web routes
│   │   └── templates/         # Jinja2 templates
│   ├── models/                # Pydantic models
│   │   ├── config.py          # Configuration models
│   │   ├── api.py             # API request/response models
│   │   └── ollama.py          # Ollama schema models
│   └── utils/                 # Utilities
├── config/                    # Configuration files
├── tests/                     # Test suite
├── docs/                      # Documentation
├── design/                    # Design documents
├── scripts/                   # Utility scripts
├── logs/                      # Application logs (auto-created)
└── data/                      # Runtime data (auto-created)
```

## 🔧 Development Status

**Current Version**: 0.8.0 (Beta)  
**Project Status**: Core features complete, multi-GPU enhancement in progress

### ✅ Phase 1: Foundation (100% Complete)
- [x] Project structure
- [x] Configuration files (YAML-based)
- [x] Configuration manager with Pydantic validation
- [x] llama.cpp process adapter
- [x] Logging system

### ✅ Phase 2: Model Lifecycle (100% Complete)
- [x] Model lifecycle manager
- [x] Load/unload/switch operations
- [x] Process health monitoring
- [x] Auto-restart on crash

### ✅ Phase 3: REST API Layer (100% Complete)
- [x] FastAPI application
- [x] Ollama-compatible endpoints
  - [x] `/api/generate` - Text generation
  - [x] `/api/chat` - Chat completion
  - [x] `/api/tags` - List models
  - [x] `/api/show` - Show model info
  - [x] `/api/ps` - Running models
- [x] Management API endpoints
  - [x] `/api/v1/models/load` - Load model
  - [x] `/api/v1/models/unload` - Unload model
  - [x] `/api/v1/models/status` - Model status
- [x] Request/response streaming support
- [x] Automatic OpenAPI documentation at `/docs`

### ✅ Phase 4: Authentication (100% Complete)
- [x] SQLite database with SQLAlchemy
- [x] User authentication (bcrypt password hashing)
- [x] Session-based authentication for Web UI
- [x] API token system with CRUD operations
- [x] Token validation middleware
- [x] Audit logging
- [x] Security features (rate limiting, login lockout)

### ✅ Phase 5: Web UI (100% Complete)
- [x] Modern responsive interface (Tailwind CSS + HTMX + Alpine.js)
- [x] Login page with authentication
- [x] Dashboard for model management
- [x] Load/unload/switch model controls
- [x] API token management interface
- [x] Server logs viewer
- [x] Real-time status updates via HTMX

### 🔄 Phase 6: Multi-GPU Enhancement & GPU Status Detection (40% Complete)
**Goal**: Support loading models on specific GPUs (GPU 0, GPU 1, or both), with robust GPU status detection

- [x] GPU configuration models (ports: 8081, 8088)
- [x] Adapter GPU parameter support (tensor-split)
- [x] Web UI GPU selection interface (toggle buttons)
- [x] Dashboard GPU status display (per-GPU cards)
- [x] Real-time GPU status detection (idle/model-loaded/occupied-by-others)
- [x] Mock GPU testing (configurable mock data for offline/dev environments)
- [x] Automatic refresh & manual refresh on model load/unload
- [x] Button disable logic for occupied/running GPUs
- [ ] Lifecycle manager multi-instance support
- [ ] API endpoints GPU parameter support
- [ ] Request routing to correct GPU instance
- [ ] Comprehensive multi-GPU testing

**Multi-GPU & GPU Status Features:**
- Load different models on different GPUs simultaneously
- Each GPU uses its own port (GPU 0: 8081, GPU 1: 8088)
- Support for single GPU or both GPUs with tensor splitting
- Web UI shows status of each GPU independently
- GPU status detection: idle, model loaded, occupied by others
- Mock mode: test GPU status logic without real GPU hardware
- Dashboard buttons auto-disable for occupied/running GPUs
- Status refresh interval optimized (5min), manual refresh on actions

### 📝 Phase 7: Testing & Documentation (70% Complete)
- [x] Unit tests for core modules
- [x] Integration tests for API and auth
- [x] Configuration validation tests
- [x] GPU status detection tests (`scripts/test_gpu_detection.py`)
- [x] GPU refresh improvements tests (`scripts/test_gpu_refresh_improvements.py`)
- [x] Mock GPU scenario tests (`tests/mock/scenarios/`)
- [x] User documentation
  - [x] QUICKSTART.md
  - [x] API_TEST_REPORT.md
  - [x] TOKEN_AUTHENTICATION_GUIDE.md
  - [x] PARAMETER_CONFIGURATION.md
- [ ] Multi-GPU documentation
- [ ] Deployment guide
- [ ] Performance tuning guide

## 📖 Documentation

### User Guides
- [Quick Start Guide](docs/QUICKSTART.md) - Get started quickly
- [Token Authentication](docs/TOKEN_AUTHENTICATION_GUIDE.md) - API token usage
- [Parameter Configuration](docs/PARAMETER_CONFIGURATION.md) - Model parameters

### User Manual (English)
- [Introduction](docs/user-manual-01-intro.md)
- [Installation & Setup](docs/user-manual-02-installation.md)
- [Basic Usage](docs/user-manual-03-usage.md)
- [API Reference](docs/user-manual-04-api.md)
- [Multi-GPU Features](docs/user-manual-05-multi-gpu.md)
- [Web UI Guide](docs/user-manual-06-web-ui.md)
- [Troubleshooting](docs/user-manual-07-troubleshooting.md)
- [Testing Best Practices](docs/user-manual-08-testing.md)

### Technical Documentation
- [Project Overview](design/01-overview.md)
- [Enhancement Requirements](design/02-enhancement-requirements.md)
- [Development Setup](design/03-development-setup.md)
- [Architecture](design/04-architecture.md)
- [Implementation Guide](design/05-implementation-guide.md)
- [Testing Best Practices](design/06-testing-best-practices.md)
- [GPU Status Detection](docs/GPU_STATUS_DETECTION.md)
- [GPU Refresh Improvements](docs/GPU_REFRESH_IMPROVEMENTS.md)
- [GPU Mock Testing](docs/GPU_MOCK_TESTING.md)
- [Air-Gap Fix](docs/AIR_GAP_FIX.md)

### Test Reports
- [API Test Report](docs/API_TEST_REPORT.md)
- [Authentication Test Report](docs/AUTH_TEST_REPORT.md)

## 🛠️ API Usage Examples

### Using Ollama-Compatible API

```bash
curl http://localhost:3000/api/tags
curl -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "phi-4-reasoning","prompt": "Explain quantum computing"}'
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "phi-4-reasoning","messages": [{"role": "user", "content": "Hello!"}]}'
```

### Using Management API

```bash
curl -X POST http://localhost:3000/api/v1/models/load \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_id": "phi-4-reasoning"}'
curl http://localhost:3000/api/v1/models/status \
  -H "Authorization: Bearer YOUR_API_TOKEN"
curl -X POST http://localhost:3000/api/v1/models/unload \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### GPU Status API

```bash
curl -X GET http://localhost:3000/gpu/status
curl -X GET http://localhost:3000/gpu/count
curl -X GET http://localhost:3000/gpu/config
```

## 🧪 Running Tests

```powershell
pytest
pytest tests/test_api.py
pytest --cov=src/llamacontroller --cov-report=html
python scripts/test_api_endpoints.py
python scripts/test_auth_endpoints.py
python scripts/test_gpu_detection.py
python scripts/test_gpu_refresh_improvements.py
```

## 🔒 Security Notes

- Default admin credentials should be changed immediately
- API tokens should be kept secure and not committed to version control
- Use HTTPS in production environments
- Configure CORS appropriately for production
- Review audit logs regularly
- Keep llama.cpp server on localhost only (not exposed externally)

## 🚧 Known Limitations

- Single model loaded at a time per GPU (multi-model support planned)
- Multi-GPU feature requires lifecycle manager refactoring (in progress)
- No GPU memory monitoring yet (planned)
- Session timeout is fixed at 1 hour (configurable in future)
- WebSocket real-time GPU status not yet implemented
- Air-gap support uses full Tailwind CDN script (consider CLI build for production)

## 🗺️ Roadmap

### Short Term (v0.9)
- [ ] Complete multi-GPU lifecycle manager support
- [ ] GPU request routing logic
- [ ] Multi-GPU integration tests
- [ ] Multi-GPU documentation
- [ ] WebSocket real-time GPU status
- [ ] GPU memory usage chart

### Medium Term (v1.0)
- [ ] GPU memory monitoring
- [ ] Model preloading for faster switching
- [ ] Advanced rate limiting
- [ ] Prometheus metrics export
- [ ] Air-gap Tailwind CSS optimization

### Long Term (v2.0+)
- [ ] Multiple models per GPU
- [ ] Distributed deployment support
- [ ] Model download from HuggingFace
- [ ] Automatic GPU selection based on load
- [ ] Model quantization support
- [ ] AMD GPU support

## 🤝 Contributing

This project is currently in active development. Contributions are welcome!

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

### Coding Standards
- Follow PEP 8 style guide
- Use type hints
- Write docstrings for public functions
- Add tests for new features
- Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - The underlying inference engine
- [Ollama](https://ollama.ai/) - API specification inspiration
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [HTMX](https://htmx.org/) - Dynamic HTML interactions

## 📞 Support

For issues and questions:
- Check the [documentation](docs/)
- Review [work logs](work_log/) for implementation details
- Open an issue on GitHub (when available)

---

**Status**: Beta - Core features complete, multi-GPU in progress  
**Version**: 0.8.0  
**Last Updated**: 2025-11-14  
**Python**: 3.8+  
**License**: MIT
