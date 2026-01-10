# Backend Architecture & Design

## Directory Structure
The backend is refactored into a modular architecture to separate concerns.

```
backend/
├── agents/             # AI Agent Implementations
│   ├── base.py         # Abstract Base Class (AgentStrategy)
│   └── implementations.py # Specific Agents (Requirement, Code, etc.)
├── core/               # Core Utilities
│   ├── logging_config.py # Custom Logging with MemoryHandler
│   ├── redis_client.py   # Redis Connection & Queue Ops
│   ├── schemas.py        # Pydantic Models
│   └── telegram_bot.py   # Telegram Notification Utility
├── routers/            # API Route Handlers
│   ├── agent_router.py   # Agent Ops & Pending items
│   ├── file_router.py    # File System Ops
│   └── workflow_router.py # Workflow Engine Ops
├── workflow/           # State Machine Engine
│   ├── models.py         # WorkItem, WorkflowEvent models
│   ├── orchestrator.py   # State Transition Logic
│   └── workflow_definition.py # State/Transition Rules
└── main.py             # App Entry Point & DI
```

## Key Modules

### 1. Agents Module
- **Strategy Pattern**: All agents inherit from `AgentStrategy`.
- **Dynamic Registry**: `AGENT_REGISTRY` maps agent names to instances.
- **Event-Driven**: Agents consume from their specific Redis queue and push to the next queue.

### 2. Workflow Engine
- **Orchestrator**: Central class managing state transitions.
- **WorkItem**: Represents a task moving through the pipeline.
- **Multi-Approval**: Supports states like `DESIGN` requiring multiple approvals (UX + Architect).

### 3. Human-in-the-loop (HITL)
- **Clarification**: Agents can pause and request user input via `needs_clarification` flag.
- **Approval**: Critical states (Design, Release) require explicit user approval.
- **Notification**: Integrated with Telegram and Web Dashboard.

## Data Flow
1. **Ingest**: Task received via API (`/event/ingest`).
2. **Queueing**: Task pushed to `queue:REQUIREMENT`.
3. **Processing**: Agent consumes event, processes it (LLM call equivalent), and modifies state.
4. **Transition**:
   - Success -> Push to next agent's queue.
   - Clarification -> Saved to `waiting:clarification:*`, Notify User.
   - Approval -> State changed to `DESIGN`, Notify User.
5. **Completion**: Final state reached or error logged.
