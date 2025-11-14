@echo off
REM Mock nvidia-smi script for testing GPU detection
REM This script simulates nvidia-smi output for testing purposes

REM Check if a custom mock file is specified via environment variable
if defined NVIDIA_SMI_MOCK_FILE (
    if exist "%NVIDIA_SMI_MOCK_FILE%" (
        type "%NVIDIA_SMI_MOCK_FILE%"
        exit /b 0
    )
)

REM Default: Use the standard mock data file
set SCRIPT_DIR=%~dp0
set MOCK_FILE=%SCRIPT_DIR%gpu_output.txt

if exist "%MOCK_FILE%" (
    type "%MOCK_FILE%"
    exit /b 0
) else (
    echo Error: Mock data file not found: %MOCK_FILE% >&2
    exit /b 1
)
