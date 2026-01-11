# Backend Architecture & Design

## Directory Structure
```
backend/
├── agents/                 # AI Agent Implementations
│   ├── base.py             # Abstract Base Class (AgentStrategy)
│   ├── implementations.py  # Re-exports from list/
│   └── list/               # Individual Agent Files
│       ├── requirement_agent.py  # + RAG 컨텍스트 조회
│       ├── plan_agent.py
│       ├── uxui_agent.py
│       ├── architect_agent.py
│       ├── code_agent.py         # Claude CLI 기본
│       ├── refactoring_agent.py  # Cursor CLI 기본
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
│   ├── llm.py              # LLM Service (Adapter pattern)
│   ├── llm_adapter.py      # Multi-LLM Adapters (NEW)
│   ├── llm_settings.py     # Per-agent LLM settings (NEW)
│   ├── database.py         # SQLite Database (NEW)
│   ├── rag_service.py      # RAG with ChromaDB (NEW)
│   ├── rag_scheduler.py    # Periodic Indexing (NEW)
│   ├── git_service.py      # Git Operations (Clone, Commit, PR)
│   ├── prompt_manager.py   # YAML Prompt Loader
│   ├── metrics_service.py  # Agent Performance Metrics (Redis)
│   └── worker.py           # Background Queue Processor (NEW)
├── routers/                # API Route Handlers
│   ├── agent_router.py     # Agent Ops & Pending items
│   ├── file_router.py      # File System Ops
│   ├── workflow_router.py  # Workflow Engine Ops
│   ├── system_router.py    # Self-Restart API
│   ├── metrics_router.py   # Metrics API
│   └── settings_router.py  # LLM & Repo Settings (NEW)
├── data/                   # Persistent Data (NEW)
│   ├── settings.db         # SQLite Database
│   ├── repos/              # Cloned repositories
│   └── rag/chroma/         # ChromaDB vectors
├── prompts.yaml            # Agent Prompt Templates
└── main.py                 # App Entry Point
```

## Key Modules

### 1. Agents Module (11 Agents)
- **Strategy Pattern**: All agents inherit from `AgentStrategy`.
- **Modular Files**: Each agent in separate file under `agents/list/`.
- **YAML Prompts**: Prompts loaded from `prompts.yaml` via `PromptManager`.
- **`get_llm_service()`**: Base class method returns agent-specific LLM adapter.

### 2. Multi-LLM Adapter System (NEW)
- **OpenAIAdapter**: GPT-4o via API
- **ClaudeCliAdapter**: Claude via `claude` CLI (CODE agent 기본)
- **CursorCliAdapter**: Cursor via `cursor` CLI (REFACTORING agent 기본)
- 에이전트별 설정은 SQLite `llm_settings` 테이블에 저장

### 3. RAG Service (NEW)
- **ChromaDB**: 벡터 저장소
- **OpenAI Embeddings**: text-embedding-3-small
- **RAG Scheduler**: 10분마다 등록된 repo 자동 인덱싱
- REQUIREMENT Agent가 관련 코드 컨텍스트 조회

### 4. Human-in-the-loop (HITL)
- **Clarification**: `needs_clarification` → 대기 및 텔레그램 알림
- **Approval**: `needs_approval` → 승인 대기 (NEW)
- **Error Stop**: `has_error` → 파이프라인 중단 (NEW)

### 5. Background Worker
- `worker.py`에서 2초마다 큐 체크 및 처리
- 에러 발생 시 파이프라인 중단
- 승인/질문 요청 시 대기 상태로 전환

## Data Flow
1. **Ingest**: Task via `/event/ingest` → `queue:REQUIREMENT`
2. **RAG Query**: REQUIREMENT Agent가 관련 코드 조회
3. **Processing**: Each agent processes and pushes to next queue
4. **Approval Gates**: 필요시 대기 (waiting:approval:*)
5. **Git Ops**: CODE/TESTQA/DOC agents commit files to feature branch
6. **PR Creation**: DOC agent creates GitHub Pull Request
7. **Evaluation**: EVALUATION agent scores achievement & records metrics

