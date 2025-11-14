# 6. Web UI Guide

LlamaController provides a user-friendly Web UI for managing models, GPUs, tokens, and viewing system status.

## Logging In

- Access the Web UI at `http://localhost:3000`
- Enter your username and password to log in

## Dashboard Overview

- View loaded models and their status
- See GPU assignments, port numbers, and memory usage
- Load, unload, or switch models directly from the dashboard

## Loading Models

- Select a model from the dropdown list
- Choose one or more GPUs using toggle buttons or checkboxes
- Click "Load Model" to start the model on selected GPU(s)

## GPU Selection Controls

- Toggle buttons or checkboxes allow flexible GPU selection
- Selected GPUs are displayed before loading
- Only available GPUs can be selected

## API Token Management

- Navigate to the "Tokens" page to create, view, or revoke API tokens
- Use tokens for authenticating API requests

## Viewing Logs

- Access the "Logs" page to view recent system and model logs
- Useful for troubleshooting and monitoring

## Accessing API Documentation

- Authenticated users can access the llama.cpp API UI (Swagger) via the navigation link
- Interactive API testing is available through the integrated documentation

## Troubleshooting via Web UI

- Error messages and status indicators are shown in the dashboard
- Use logs and model status to diagnose issues

---
