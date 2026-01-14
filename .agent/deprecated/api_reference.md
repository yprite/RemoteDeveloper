# API Reference

Backend Server API Endpoints Documentation.

Base URL: `http://localhost:8000`

## 1. System Control (`/system/*`)

### Get System Status
Returns the current status of backend services and components.

- **URL**: `GET /system/status`
- **Response**:
  ```json
  {
    "status": "ok",
    "timestamp": "2024-01-01T12:00:00.000000",
    "debugMode": true,
    "redis": "running",
    "services": {
      "n8n": "running"
    }
  }
  ```

### Restart System
Triggers a self-restart of the backend server.

- **URL**: `POST /system/restart`
- **Response**: `{"status": "restarting", "message": "Server is restarting..."}`

### N8N Service Control
Manage the local n8n workflow service.

- **URL**: `POST /system/n8n/{action}`
- **Parameters**: `action` = `start` | `stop` | `restart`
- **Response**: `{"status": "success", "action": "start"}`

---

## 2. Settings & RAG (`/settings/*`)

### LLM Settings
Configure LLM adapters for each agent.

- **Get Settings**: `GET /settings/llm`
- **Update Setting**: `POST /settings/llm`
  - **Body**: `{"agent_name": "CODE", "adapter": "ClaudeCliAdapter"}`

### Repository Settings (RAG)
Manage Git repositories for RAG knowledge base.

- **List Repos**: `GET /settings/repos`
- **Add Repo**: `POST /settings/repos`
  - **Body**: `{"url": "https://github.com/user/repo", "name": "backend"}`
- **Delete Repo**: `DELETE /settings/repos/{id}`
- **Reindex**: `POST /settings/repos/reindex`

### Debug Mode
Toggle global debug mode. When enabled, agent tasks are paused in "Pending" state until approved.

- **URL**: `POST /settings/debug`
- **Body**: `{"enabled": true}`

---

## 3. Tasks & Events

### Task Management
View task history and details.

- **List Tasks**: `GET /tasks`
  - **Query**: `?limit=50&offset=0`
- **Get Task Detail**: `GET /tasks/{task_id}`

### Agent History
Get processing history for a specific agent.

- **URL**: `GET /agent/{agent_name}/history`
- **Query**: `?limit=20`

### Pipeline Pending Items
Get items waiting for clarification, approval, or debug execution.

- **URL**: `GET /pending`
- **Response**:
  ```json
  {
    "clarification": [],
    "approval": [],
    "debug": []
  }
  ```
- **Approve Item**: `POST /workitem/{id}/approve`

### Event Ingestion
Trigger a new task from external sources (e.g., Telegram, n8n).

- **URL**: `POST /event/ingest`
- **Body**:
  ```json
  {
    "event": "user_request",
    "task": {
      "original_prompt": "Fix login bug"
    }
  }
  ```
