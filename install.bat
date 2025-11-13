@echo off
REM LlamaController Installation Script (pip/setuptools)
REM For UV installation, use install_uv.bat instead

echo ========================================
echo LlamaController Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Python found:
python --version
echo.

REM Check if we're in a conda environment
if defined CONDA_DEFAULT_ENV (
    echo [2/4] Conda environment: %CONDA_DEFAULT_ENV%
) else (
    echo [2/4] No conda environment detected
    echo TIP: Consider using conda environment:
    echo   conda create -n llamacontroller python=3.11 -y
    echo   conda activate llamacontroller
)
echo.

REM Upgrade pip
echo [3/4] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install the package in editable mode
echo [4/4] Installing LlamaController...
python -m pip install -e .

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Installation failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Start LlamaController:
echo   - start.bat
echo   - python -m llamacontroller
echo   - llamacontroller
echo.
echo For development mode (auto-reload):
echo   - start_dev.bat
echo.
pause