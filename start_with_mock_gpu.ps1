# Start LlamaController with mock GPU detection
# This script sets up the PATH to use mock nvidia-smi for testing

Write-Host "Setting up mock GPU environment..." -ForegroundColor Cyan

# Add mock directory to PATH
$env:PATH += ";$PWD\tests\mock"

Write-Host "Mock nvidia-smi path added to PATH" -ForegroundColor Green
Write-Host "Starting LlamaController..." -ForegroundColor Cyan
Write-Host ""

# Start the application
python run.py
