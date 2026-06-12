# AgentForge API Specification

Welcome to the AgentForge API reference docs. AgentForge provides a developer-friendly REST & WebSocket interface to control local LLM nodes, visual workflows, ComfyUI instances, and Model Context Protocol (MCP) integrations.

---

## Authentication

Authentication uses standard OAuth2 Bearer Tokens (JWT). 

Include the token in all HTTP headers:
```http
Authorization: Bearer <your_access_token>
```

---

## REST API Endpoint Reference

### 1. Model Context Protocol (MCP) Manager

#### Register an MCP Server
* **Endpoint:** `/api/v1/mcp/servers`
* **Method:** `POST`
* **Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "name": "sqlite-connector",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "--db-uri", "postgresql://localhost/mydb"],
  "env": {
    "DEBUG": "true"
  }
}
```
* **Response (201 Created):**
```json
{
  "id": "e3b0c442-98fc-11ee-b9d1-0242ac120002",
  "name": "sqlite-connector",
  "status": "offline",
  "created_at": "2026-06-12T18:00:00Z"
}
```

#### Reload/Refresh an MCP Server
* **Endpoint:** `/api/v1/mcp/servers/{id}/reload`
* **Method:** `POST`
* **Response (200 OK):**
```json
{
  "id": "e3b0c442-98fc-11ee-b9d1-0242ac120002",
  "name": "sqlite-connector",
  "status": "running",
  "tools_discovered": [
    {
      "name": "query_db",
      "description": "Execute read-only SQL queries on the active database"
    }
  ]
}
```

---

### 2. Local AI Hub (Ollama / LM Studio)

#### List Loaded Local Models
* **Endpoint:** `/api/v1/hub/models`
* **Method:** `GET`
* **Response (200 OK):**
```json
{
  "models": [
    {
      "name": "deepseek-coder:6.7b",
      "size_bytes": 3820198000,
      "details": {
        "format": "gguf",
        "family": "llama",
        "parameter_size": "7B"
      }
    }
  ]
}
```

#### Download / Pull a Model
* **Endpoint:** `/api/v1/hub/download`
* **Method:** `POST`
* **Request Body:**
```json
{
  "model_name": "llama3:8b"
}
```
* **Response (202 Accepted):**
```json
{
  "status": "pulling",
  "message": "Model download initiated in the background."
}
```

---

### 3. Agent System

#### Create an Agent Profile
* **Endpoint:** `/api/v1/agents`
* **Method:** `POST`
* **Request Body:**
```json
{
  "name": "SearchForge",
  "description": "Performs deep web parsing and summaries",
  "system_prompt": "You are a professional research agent...",
  "model_provider": "ollama",
  "model_name": "llama3:8b",
  "temperature": 0.3,
  "tools_enabled": ["web_search", "file_manager"]
}
```
* **Response (201 Created):**
```json
{
  "id": "7fa82b26-a36c-4861-bd8f-f7d97b0a7018",
  "name": "SearchForge",
  "status": "active"
}
```

---

## WebSocket Event Interface

AgentForge uses WebSockets to stream LLM responses and track active tool parameters.

### WS Server URL:
```ws
ws://localhost:8000/api/v1/ws/chat/{conversation_id}
```

### Server-to-Client Messages

#### 1. Real-time Tokens
Sent when the agent streams a text response.
```json
{
  "type": "token",
  "content": "Using the Web Search tool to find "
}
```

#### 2. Tool Invocation Start
Sent when the agent triggers an internal tool/MCP function.
```json
{
  "type": "tool_start",
  "tool_name": "web_search",
  "arguments": {
    "query": "Model Context Protocol specifications"
  }
}
```

#### 3. Tool Invocation Complete
Sent when the tool completes run.
```json
{
  "type": "tool_end",
  "tool_name": "web_search",
  "status": "success",
  "result": "Discovered specification document at modelcontextprotocol.org..."
}
```
