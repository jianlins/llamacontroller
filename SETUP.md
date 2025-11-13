# LlamaController Setup Guide

This project uses **Conda** for Python environment management and **UV** for fast package installation.

## Prerequisites

- Conda (Miniforge/Miniconda/Anaconda)
- No admin rights required!

## Quick Setup

### Option 1: Automated Setup (Recommended)

Run the setup script:

```powershell
.\setup.ps1
```

### Option 2: Manual Setup

#### Step 1: Create Conda Environment

```powershell
conda env create -f environment.yml
```

This installs:
- Python 3.11
- pip
- uv (fast package installer)

#### Step 2: Activate Environment

```powershell
conda activate llamacontroller
```

#### Step 3: Install Dependencies with UV

Install project in editable mode with dev dependencies:

```powershell
uv pip install -e ".[dev]"
```

Or without dev dependencies:

```powershell
uv pip install -e .
```

## Why This Setup?

### Conda for Environment
- ✅ Python version management
- ✅ Works without admin rights
- ✅ Isolated environments
- ✅ Easy to install uv

### UV for Packages
- ⚡ **10-100x faster** than pip
- 🔒 Better dependency resolution
- 💾 Global cache (saves disk space)
- 🎯 Drop-in pip replacement

## Common Commands

### Managing Dependencies

```powershell
# Add a new package
uv pip install package-name

# Add to pyproject.toml manually, then sync
uv pip install -e ".[dev]"

# Update all packages
uv pip install --upgrade -e ".[dev]"

# List installed packages
uv pip list

# Freeze dependencies
uv pip freeze > requirements-lock.txt
```

### Running the Application

```powershell
# Run directly
python -m llamacontroller.main

# Or use the entry point (after installation)
llamacontroller
```

### Development Tools

```powershell
# Run tests
pytest

# Run tests with coverage
pytest --cov

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Environment Management

### Update Environment

If you update `environment.yml`:

```powershell
conda env update -f environment.yml
```

### Remove Environment

```powershell
conda deactivate
conda env remove -n llamacontroller
```

### Export Environment

```powershell
# Export conda environment
conda env export > environment-lock.yml

# Export uv packages (for pip compatibility)
uv pip freeze > requirements-lock.txt
```

## Troubleshooting

### UV not found after conda install

```powershell
conda activate llamacontroller
conda install -c conda-forge uv
```

### Slow package installation

UV should be fast. If it's slow, ensure you're using uv:

```powershell
uv pip install package-name  # Fast ⚡
pip install package-name     # Slower 🐌
```

### Import errors

Make sure you installed in editable mode:

```powershell
uv pip install -e .
```

## VS Code Integration

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${env:CONDA_PREFIX}/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true
}
```

## Notes

- All project dependencies are in `pyproject.toml`
- `environment.yml` only contains Python + package managers
- UV reads dependencies from `pyproject.toml` automatically
- No `requirements.txt` needed (UV uses `pyproject.toml`)
