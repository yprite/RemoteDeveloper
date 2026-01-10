# System Architecture

## Overview
This system is an **AI-driven Product Development Platform** designed to automate software creation workflow using a multi-agent architecture. It integrates a web dashboard, Python backend, Redis message queue, and n8n for external workflow orchestration.

## High-Level Architecture

```mermaid
graph TD
    User[User / Developer] -->|Access| Cloudflare[Cloudflare Tunnels]
    Cloudflare -->|HTTPS| FE[Frontend Dashboard (Vite/React)]
    Cloudflare -->|HTTPS| BE[Backend API (FastAPI)]
    Cloudflare -->|HTTPS| N8N[n8n Workflow Automation]
    
    FE -->|API Calls| BE
    
    subgraph "Backend System"
        BE -->|Events| Redis[Redis (Message Queue & State Store)]
        Redis -->|Consume| Agents[AI Agents (Worker Pool)]
        Agents -->|Pub/Sub| Redis
        
        Orchestrator[Workflow Orchestrator] <-->|Manage| Redis
    end
    
    subgraph "External Integrations"
        N8N -->|Webhooks| BE
        Telegram[Telegram Bot] <-->|Notifications| BE
    end
```

## Component Details

### 1. Frontend Dashboard (Vite + React)
- **Role**: User Interface for monitoring and interacting with the AI pipeline.
- **Features**:
  - Real-time Log Streaming
  - Agent Status Monitoring
  - **Pending Actions Tab**: Human-in-the-loop interface for clarifications & approvals.
  - Interactive Pipeline Visualization.

### 2. Backend (FastAPI + Python)
- **Role**: Core logic provider, API gateway, and agent host.
- **Structure**:
  - `main.py`: Application entry point.
  - `routers/`: API endpoints (`/agent`, `/workflow`, `/pending`).
  - `agents/`: AI Agent implementations (Requirement, Plan, Code, etc.).
  - `core/`: Shared utilities (Redis, Logging, Telegram).
  - `workflow/`: State machine engine (Orchestrator, WorkItem).

### 3. Redis
- **Role**: Central communication hub (Event Bus) and state persistence.
- **Usage**:
  - **Agent Queues**: `queue:REQUIREMENT`, `queue:PLAN`, etc.
  - **WorkItem Storage**: Persistence for workflow state.
  - **Logs**: In-memory log buffer for frontend streaming.

### 4. n8n
- **Role**: External workflow automation and initial trigger handling.
- **Flow**: Telegram -> n8n -> OpenAI (Refinement) -> Backend Ingest.

### 5. Cloudflare Tunnels
- **Role**: Expose local services to the public internet securely (HTTPS).
- **Services**: Frontend, Backend, n8n.

## Deployment & Startup
- Managed by `start_system.py`.
- Launches all services and establishes tunnels automatically.
- Sends access URLs to Telegram upon successful startup.
