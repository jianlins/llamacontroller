# Implementation Guide & Recommendations

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Goal**: Basic infrastructure and configuration management

- [ ] Set up project structure
- [ ] Implement configuration manager
  - [ ] YAML parsing
  - [ ] Validation logic
  - [ ] Model and llama.cpp config loading
- [ ] Implement llama.cpp process adapter
  - [ ] Subprocess management
  - [ ] Health check logic
  - [ ] Log capture
- [ ] Basic logging setup
- [ ] Unit tests for core modules

**Deliverable**: Can start/stop llama-server with a model

### Phase 2: Model Lifecycle (Week 2-3)
**Goal**: Full model management capabilities

- [ ] Implement Model Lifecycle Manager
  - [ ] Load model operation
  - [ ] Unload model operation
  - [ ] Switch model operation
  - [ ] Status tracking
- [ ] Handle llama.cpp crashes and restarts
- [ ] Resource monitoring (optional)
- [ ] Integration tests for model operations

**Deliverable**: Can load, unload, and switch models reliably

### Phase 3: API Layer (Week 3-4)
**Goal**: Ollama-compatible REST API

- [ ] Set up FastAPI application
- [ ] Implement core Ollama endpoints
  - [ ] POST /api/generate
  - [ ] POST /api/chat
  - [ ] GET /api/tags
  - [ ] POST /api/show
  - [ ] GET /api/ps
- [ ] Request/response transformation
- [ ] Streaming support
- [ ] Error handling and validation
- [ ] API tests against Ollama spec

**Deliverable**: Ollama-compatible applications can connect

### Phase 4: Authentication (Week 4-5)
**Goal**: Secure access control

- [ ] Database schema design (SQLite)
- [ ] User authentication
  - [ ] Password hashing
  - [ ] Login endpoint
  - [ ] Session management
- [ ] API token system
  - [ ] Token generation
  - [ ] Token validation middleware
  - [ ] CRUD operations
- [ ] Rate limiting
- [ ] Security tests

**Deliverable**: Secure authentication for both UI and API

### Phase 5: Web UI (Week 5-6)
**Goal**: User-friendly management interface

- [ ] UI framework setup (HTMX + Jinja2 recommended)
- [ ] Login page
- [ ] Dashboard
  - [ ] Model list
  - [ ] Current model status
  - [ ] Load/unload/switch controls
- [ ] Token management interface
- [ ] Configuration viewer/editor (optional)
- [ ] Logs viewer
- [ ] UI/UX testing

**Deliverable**: Complete web interface for management

### Phase 6: Testing & Documentation (Week 6-7)
**Goal**: Production-ready system

- [ ] Comprehensive testing
  - [ ] Unit tests (80%+ coverage)
  - [ ] Integration tests
  - [ ] End-to-end tests
  - [ ] Load testing
- [ ] User documentation
  - [ ] Installation guide
  - [ ] Configuration guide
  - [ ] API documentation
  - [ ] Troubleshooting guide
- [ ] Developer documentation
  - [ ] Code documentation
  - [ ] Architecture diagrams
  - [ ] Contribution guide
- [ ] Deployment scripts

**Deliverable**: Deployable, documented system

## Technology Recommendations

### Python Framework: FastAPI

**Why FastAPI?**
- Modern, fast, and well-documented
- Built-in async support (essential for proxying)
- Automatic OpenAPI documentation
- Type hints and validation with Pydantic
- Easy to test
- Growing community

**Setup**:
\\\ash
conda activate llama.cpp
pip install "fastapi[all]" uvicorn[standard] python-multipart
\\\

### Database: SQLite + SQLAlchemy

**Why SQLite?**
- No separate server process
- File-based, easy backup
- Sufficient for single-server deployment
- Easy to migrate to PostgreSQL later

**Setup**:
\\\ash
pip install sqlalchemy alembic
\\\

### UI: HTMX + Tailwind CSS + Jinja2

**Why HTMX?**
- Modern interactivity without complex JS build
- Works with server-side templates
- Progressive enhancement
- Easy to learn

**Alternatives**:
- Pure Jinja2: Simplest, full page reloads
- React/Vue: Best UX, but requires build process and more complexity

**Setup**:
\\\ash
pip install jinja2
# HTMX and Tailwind loaded via CDN in templates
\\\

### Authentication: bcrypt + JWT

**Setup**:
\\\ash
pip install bcrypt python-jose[cryptography] passlib
\\\

### Configuration: PyYAML

**Setup**:
\\\ash
pip install pyyaml python-dotenv
\\\

### HTTP Client: httpx

**Why httpx?**
- Async support for proxying to llama.cpp
- Similar API to requests
- Better performance

**Setup**:
\\\ash
pip install httpx
\\\

### Testing: pytest

**Setup**:
\\\ash
pip install pytest pytest-asyncio pytest-cov httpx
\\\

## Recommended Project Structure

\\\
llamacontroller/
├── README.md
├── requirements.txt                 # Python dependencies
├── setup.py or pyproject.toml       # Package configuration
├── .env.example                     # Example environment variables
├── .gitignore
│
├── config/                          # Configuration files (not in git except examples)
│   ├── llamacpp-config.yaml
│   ├── models-config.yaml
│   └── auth-config.yaml
│
├── src/
│   └── llamacontroller/
│       ├── __init__.py
│       ├── main.py                  # FastAPI app entry point
│       │
│       ├── core/                    # Core business logic
│       │   ├── __init__.py
│       │   ├── config.py            # Configuration management
│       │   ├── lifecycle.py         # Model lifecycle manager
│       │   └── adapter.py           # llama.cpp adapter
│       │
│       ├── api/                     # API routes
│       │   ├── __init__.py
│       │   ├── ollama.py            # Ollama-compatible endpoints
│       │   ├── management.py        # Management endpoints
│       │   └── dependencies.py      # FastAPI dependencies
│       │
│       ├── auth/                    # Authentication
│       │   ├── __init__.py
│       │   ├── service.py           # Auth service
│       │   ├── models.py            # Auth data models
│       │   └── utils.py             # Hashing, tokens
│       │
│       ├── db/                      # Database
│       │   ├── __init__.py
│       │   ├── base.py              # SQLAlchemy base
│       │   ├── models.py            # DB models
│       │   └── crud.py              # CRUD operations
│       │
│       ├── web/                     # Web UI
│       │   ├── __init__.py
│       │   ├── routes.py            # UI routes
│       │   ├── templates/           # Jinja2 templates
│       │   │   ├── base.html
│       │   │   ├── login.html
│       │   │   ├── dashboard.html
│       │   │   └── tokens.html
│       │   └── static/              # Static assets
│       │       ├── css/
│       │       └── js/
│       │
│       ├── models/                  # Pydantic models
│       │   ├── __init__.py
│       │   ├── config.py            # Config models
│       │   ├── api.py               # API request/response models
│       │   └── ollama.py            # Ollama schema models
│       │
│       └── utils/                   # Utilities
│           ├── __init__.py
│           ├── logging.py
│           └── validators.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_config.py
│   ├── test_lifecycle.py
│   ├── test_adapter.py
│   ├── test_api_ollama.py
│   ├── test_auth.py
│   └── integration/
│       └── test_end_to_end.py
│
├── docs/                            # User documentation
│   ├── installation.md
│   ├── configuration.md
│   ├── api.md
│   └── troubleshooting.md
│
├── design/                          # Design documents (these files)
│   ├── 01-overview.md
│   ├── 02-requirements.md
│   ├── 03-development-setup.md
│   ├── 04-architecture.md
│   └── 05-implementation-guide.md
│
├── scripts/                         # Utility scripts
│   ├── init_db.py                   # Initialize database
│   ├── create_user.py               # Create admin user
│   └── generate_token.py            # Generate API token
│
├── logs/                            # Application logs (gitignored)
└── data/                            # Runtime data (gitignored)
    └── llamacontroller.db
\\\

## Development Best Practices

### 1. Code Quality

- **Type Hints**: Use Python type hints everywhere
- **Docstrings**: Document all public functions and classes
- **Linting**: Use ruff or flake8
- **Formatting**: Use black or ruff format
- **Pre-commit Hooks**: Automate quality checks

\\\ash
pip install ruff black mypy pre-commit
\\\

### 2. Testing Strategy

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete workflows
- **Test Coverage**: Aim for 80%+ coverage
- **Mock External Dependencies**: Mock llama.cpp in most tests

### 3. Configuration Management

- **Environment Variables**: Support for .env files
- **Configuration Validation**: Validate on startup
- **Sensible Defaults**: Provide reasonable defaults
- **Configuration Examples**: Include example configs

### 4. Error Handling

- **Custom Exceptions**: Define domain-specific exceptions
- **Logging**: Log all errors with context
- **User-Friendly Messages**: Clear error messages in API responses
- **Graceful Degradation**: Handle failures without crashing

### 5. Security

- **Input Validation**: Validate all inputs with Pydantic
- **SQL Injection**: Use SQLAlchemy ORM, never raw SQL with user input
- **XSS Prevention**: Auto-escape templates, sanitize outputs
- **Rate Limiting**: Implement on auth endpoints
- **Security Headers**: Set appropriate HTTP headers
- **Secrets Management**: Never commit secrets to git

## Configuration Examples

### requirements.txt
\\\	xt
# Web Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0

# Authentication
bcrypt>=4.0.0
python-jose[cryptography]>=3.3.0
passlib>=1.7.4

# Configuration
pyyaml>=6.0
python-dotenv>=1.0.0

# HTTP Client
httpx>=0.25.0

# Templates & UI
jinja2>=3.1.0

# Validation
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Utilities
python-dateutil>=2.8.0

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
ruff>=0.1.0
black>=23.0.0
mypy>=1.7.0
\\\

### .env.example
\\\ash
# Server Configuration
LLAMACONTROLLER_HOST=0.0.0.0
LLAMACONTROLLER_PORT=3000
LLAMACONTROLLER_DEBUG=false

# Paths
LLAMACONTROLLER_CONFIG_DIR=./config
LLAMACONTROLLER_DATA_DIR=./data
LLAMACONTROLLER_LOG_DIR=./logs

# Database
DATABASE_URL=sqlite:///./data/llamacontroller.db

# Security
SECRET_KEY=your-secret-key-here-change-in-production
SESSION_TIMEOUT=3600
TOKEN_EXPIRE_DAYS=30

# llama.cpp
LLAMACPP_EXECUTABLE=C:\\Users\\NLPDev\\software\\llamacpp\\llama-server.exe
LLAMACPP_HOST=127.0.0.1
LLAMACPP_PORT=8080

# Logging
LOG_LEVEL=INFO
\\\

## Testing Strategy

### Unit Test Example
\\\python
# tests/test_config.py
import pytest
from llamacontroller.core.config import ConfigManager

def test_load_valid_config(tmp_path):
    # Create temp config file
    config_file = tmp_path / "test-config.yaml"
    config_file.write_text("""
llama_cpp:
  executable_path: "/path/to/llama-server"
  default_port: 8080
    """)
    
    manager = ConfigManager(config_file)
    config = manager.load_config()
    
    assert config.llama_cpp.executable_path == "/path/to/llama-server"
    assert config.llama_cpp.default_port == 8080

def test_invalid_config_raises_error(tmp_path):
    config_file = tmp_path / "bad-config.yaml"
    config_file.write_text("invalid: yaml: content")
    
    manager = ConfigManager(config_file)
    with pytest.raises(ConfigError):
        manager.load_config()
\\\

### Integration Test Example
\\\python
# tests/integration/test_model_operations.py
import pytest
from llamacontroller.core.lifecycle import ModelLifecycleManager

@pytest.mark.asyncio
async def test_load_and_unload_model(lifecycle_manager, test_config):
    # Load model
    result = await lifecycle_manager.load_model("phi-4-reasoning")
    assert result.success is True
    assert lifecycle_manager.current_model is not None
    
    # Check health
    is_healthy = await lifecycle_manager.healthcheck()
    assert is_healthy is True
    
    # Unload model
    await lifecycle_manager.unload_model()
    assert lifecycle_manager.current_model is None
\\\

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance testing done
- [ ] Documentation complete
- [ ] Configuration examples provided
- [ ] Installation script tested

### Production Configuration
- [ ] Change default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS
- [ ] Set appropriate log levels
- [ ] Configure backup strategy
- [ ] Set up monitoring (optional)

### Deployment Steps
1. Install Python and dependencies
2. Create conda environment
3. Copy configuration files
4. Initialize database
5. Create admin user
6. Test llama.cpp connectivity
7. Start LlamaController service
8. Verify API endpoints
9. Test UI access
10. Configure reverse proxy (if needed)

## Common Pitfalls to Avoid

### 1. Process Management
- ❌ Don't forget to cleanup subprocess on exit
- ❌ Don't ignore llama.cpp stderr output
- ✅ Use proper signal handling for graceful shutdown

### 2. Async/Sync Mixing
- ❌ Don't mix blocking and async code
- ✅ Use httpx for async HTTP requests
- ✅ Use async database drivers or thread pools

### 3. Configuration
- ❌ Don't hardcode paths
- ❌ Don't commit secrets to git
- ✅ Support environment variables
- ✅ Provide clear validation errors

### 4. Error Handling
- ❌ Don't let llama.cpp crashes kill the controller
- ❌ Don't expose internal errors to API clients
- ✅ Log detailed errors internally
- ✅ Return user-friendly messages externally

### 5. Security
- ❌ Don't store passwords in plain text
- ❌ Don't trust user input
- ✅ Hash passwords with bcrypt
- ✅ Validate and sanitize all inputs

## Next Steps

Once you're ready to begin implementation:

1. **Review all design documents** in this folder
2. **Set up conda environment** as described in 03-development-setup.md
3. **Verify test environment** with your local llama.cpp and models
4. **Create project structure** following recommendations above
5. **Start with Phase 1** (Foundation) of the roadmap
6. **Test incrementally** after each component
7. **Document as you go** to avoid tech debt

## Questions to Consider

Before starting implementation, clarify:

- **UI Framework**: HTMX, React, or simple Jinja2?
- **Session Storage**: File-based or database?
- **Monitoring**: Built-in metrics or external tool?
- **Deployment**: Standalone Python app or Docker container?
- **Update Strategy**: Auto-update support needed?

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-11  
**Status**: Ready for Implementation

**Next Action**: Review design docs with stakeholder, then begin Phase 1 implementation
