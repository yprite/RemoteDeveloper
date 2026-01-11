# Backend Architecture & Design

## Directory Structure
```
backend/
├── agents/                 # AI Agent Implementations
│   ├── base.py             # Abstract Base Class (AgentStrategy)
│   ├── implementations.py  # Re-exports from list/
│   └── list/               # Individual Agent Files
│       ├── requirement_agent.py
│       ├── plan_agent.py
│       ├── uxui_agent.py
│       ├── architect_agent.py
│       ├── code_agent.py
│       ├── refactoring_agent.py
│       ├── test_qa_agent.py
│       ├── doc_agent.py
│       ├── release_agent.py
│       ├── monitoring_agent.py
│       └── evaluation_agent.py
├── core/                   # Core Utilities
│   ├── logging_config.py   # Custom Logging with MemoryHandler
│   ├── redis_client.py     # Redis Connection & Queue Ops
│   ├── schemas.py          # Pydantic Models
│   ├── telegram_bot.py     # Telegram Notification Utility
│   ├── llm.py              # OpenAI API Wrapper
│   ├── git_service.py      # Git Operations (Clone, Commit, PR)
│   ├── prompt_manager.py   # YAML Prompt Loader
│   └── metrics_service.py  # Agent Performance Metrics (Redis)
├── routers/                # API Route Handlers
│   ├── agent_router.py     # Agent Ops & Pending items
│   ├── file_router.py      # File System Ops
│   ├── workflow_router.py  # Workflow Engine Ops
│   ├── system_router.py    # Self-Restart API
│   └── metrics_router.py   # Metrics API
├── workflow/               # State Machine Engine
│   ├── models.py           # WorkItem, WorkflowEvent models
│   ├── orchestrator.py     # State Transition Logic
│   └── workflow_definition.py
├── prompts.yaml            # Agent Prompt Templates
└── main.py                 # App Entry Point
```

## Key Modules

### 1. Agents Module (11 Agents)
- **Strategy Pattern**: All agents inherit from `AgentStrategy`.
- **Modular Files**: Each agent in separate file under `agents/list/`.
- **YAML Prompts**: Prompts loaded from `prompts.yaml` via `PromptManager`.

### 2. Self-Improvement Features
- **LLMService**: OpenAI API integration for all agents.
- **GitService**: Clone, branch, commit, push, and PR creation.
- **SystemRouter**: `/system/restart` for hot-reload after code changes.
- **MetricsService**: Tracks agent performance (success rate, duration).

### 3. Human-in-the-loop (HITL)
- **Clarification**: Agents pause and request user input.
- **Approval**: Critical states (Design, Release, Restart) require approval.
- **Dashboard**: Stats tab shows agent performance metrics.

## Data Flow
1. **Ingest**: Task via `/event/ingest` → `queue:REQUIREMENT`
2. **Processing**: Each agent processes and pushes to next queue
3. **Git Ops**: CODE/TESTQA/DOC agents commit files to feature branch
4. **PR Creation**: DOC agent creates GitHub Pull Request
5. **Evaluation**: EVALUATION agent scores achievement & records metrics
6. **Dashboard**: Stats tab displays metrics from `/metrics/agents`
