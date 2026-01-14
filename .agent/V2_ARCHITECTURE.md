# RemoteDevelop v2 초기 구조 (권장)

다음 반복 시 참고할 디렉토리 구조입니다.

```
RemoteDevelop/
├── .agent/                     # AI 어시스턴트 참조 문서 (유지)
│   ├── README.md
│   ├── FAILURE_REGISTRY.md
│   └── workflows/
│
├── backend/
│   ├── main.py                 # FastAPI entry (< 50 lines)
│   │
│   ├── api/                    # API Layer
│   │   ├── routes/
│   │   │   ├── agents.py       # 에이전트 관련 엔드포인트
│   │   │   └── tasks.py        # 태스크 관련 엔드포인트
│   │   └── dependencies.py     # Dependency Injection
│   │
│   ├── core/                   # Orchestration Layer
│   │   ├── orchestrator.py     # 단일 진입점 (< 200 lines)
│   │   ├── queue.py            # Redis 큐 추상화
│   │   └── state.py            # 상태 관리 (Redis only)
│   │
│   ├── agents/                 # Agent Layer (순수 함수)
│   │   ├── base.py             # 간소화된 AgentStrategy
│   │   ├── planner.py          # Planning Agent
│   │   ├── coder.py            # Coding Agent
│   │   └── reviewer.py         # Review Agent
│   │
│   ├── tools/                  # Tool Layer (사이드 이펙트 격리)
│   │   ├── llm.py              # LLM 호출
│   │   ├── git.py              # Git 연산
│   │   └── rag.py              # RAG 쿼리
│   │
│   └── prompts/
│       └── agents.yaml         # 프롬프트 템플릿
│
├── frontend/                   # (선택) 대시보드
│
└── docker-compose.yml          # Redis + Backend
```

## 핵심 차이점

| 현재 (v1) | 권장 (v2) |
|-----------|-----------|
| 11개 에이전트 | 3-4개 에이전트 |
| 에이전트가 Git/LLM 직접 호출 | Orchestrator가 Tool 호출 |
| Redis + SQLite + ChromaDB | Redis only |
| Router + Worker 중복 | Orchestrator 단일 진입점 |
| 690 line router | < 200 line per file |

## 간소화된 AgentStrategy

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class AgentStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        순수 함수: context를 받아 result를 반환.
        사이드 이펙트 없음 (Git, LLM 호출 금지).
        대신 result에 필요한 action을 명시.
        """
        pass
```

## Orchestrator 책임

```python
class Orchestrator:
    def __init__(self, queue, tools):
        self.queue = queue
        self.tools = tools  # llm, git, rag
    
    def process_task(self, task_id: str):
        context = self.queue.pop(task_id)
        agent = self.get_current_agent(context)
        
        # 1. 필요하면 RAG 컨텍스트 추가
        if agent.needs_rag:
            context["rag"] = self.tools.rag.query(...)
        
        # 2. 에이전트 실행 (순수 함수)
        result = agent.process(context)
        
        # 3. 결과에 따른 액션 수행
        for action in result.get("actions", []):
            self.execute_action(action)
        
        # 4. 다음 단계로
        self.queue.push(result)
```

---

*이 문서는 참조용입니다. 필요에 따라 수정하세요.*
