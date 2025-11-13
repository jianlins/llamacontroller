#!/usr/bin/env pwsh
# Setup script for LlamaController using Conda + UV

Write-Host "🚀 Setting up LlamaController environment..." -ForegroundColor Cyan

# Step 1: Create conda environment with Python and uv
Write-Host "`n📦 Step 1: Creating conda environment..." -ForegroundColor Yellow
conda env create -f environment.yml

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create conda environment" -ForegroundColor Red
    exit 1
}

# Step 2: Activate environment
Write-Host "`n🔄 Step 2: Activating environment..." -ForegroundColor Yellow
conda activate llamacontroller

# Step 3: Install dependencies with uv
Write-Host "`n📥 Step 3: Installing dependencies with uv..." -ForegroundColor Yellow
uv pip install -e ".[dev]"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "`nTo activate the environment, run:" -ForegroundColor Cyan
Write-Host "  conda activate llamacontroller" -ForegroundColor White
Write-Host "`nTo add new dependencies:" -ForegroundColor Cyan
Write-Host "  uv pip install <package-name>" -ForegroundColor White
Write-Host "`nTo run the application:" -ForegroundColor Cyan
Write-Host "  python -m llamacontroller.main" -ForegroundColor White
