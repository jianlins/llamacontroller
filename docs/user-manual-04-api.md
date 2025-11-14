# 4. API Reference

LlamaController provides Ollama-compatible REST API endpoints for model inference and management. All API requests require authentication via Bearer token.

## Authentication

- Include your API token in the `Authorization` header:
  ```
  Authorization: Bearer <your_token>
  ```

## Endpoints

### 1. Generate Completion

**POST /api/generate**

Request:
```json
{
  "model": "phi-4-reasoning",
  "prompt": "Hello, world!"
}
```
Response:
```json
{
  "completion": "Hi! How can I help you today?"
}
```

### 2. Chat Completion

**POST /api/chat**

Request:
```json
{
  "model": "phi-4-reasoning",
  "messages": [
    {"role": "user", "content": "Tell me a joke."}
  ]
}
```
Response:
```json
{
  "reply": "Why did the llama cross the road? To get to the other side!"
}
```

### 3. List Models

**GET /api/tags**

Response:
```json
{
  "models": [
    {"id": "phi-4-reasoning", "name": "Phi-4 Reasoning Plus"},
    {"id": "qwen3-coder-30b", "name": "Qwen3 Coder 30B"}
  ]
}
```

### 4. Show Model Details

**POST /api/show**

Request:
```json
{
  "model": "phi-4-reasoning"
}
```
Response:
```json
{
  "id": "phi-4-reasoning",
  "name": "Phi-4 Reasoning Plus",
  "parameters": {...}
}
```

### 5. List Running Models

**GET /api/ps**

Response:
```json
{
  "running_models": [
    {"id": "phi-4-reasoning", "status": "running"}
  ]
}
```

### 6. Delete Model

**DELETE /api/delete**

Request:
```json
{
  "model": "phi-4-reasoning"
}
```
Response:
```json
{
  "success": true
}
```

## Error Handling

- Errors return HTTP status codes and a JSON message:
  ```json
  {
    "error": "Model not found"
  }
  ```

## API Token Management

- Generate and manage tokens in the Web UI under "Tokens".

## Advanced Features

- Multi-GPU: Use the `gpu_id` parameter when loading models via API (see Multi-GPU section).
- All endpoints support JSON requests and responses.

---
