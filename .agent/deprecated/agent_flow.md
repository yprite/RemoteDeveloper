# Agent Flowchart

Visualizes the flow of data through the **11-agent** pipeline.

```mermaid
flowchart TD
    Start((Start)) --> REQ[📋 Requirement Agent]
    
    REQ -->|Needs Clarification| WAIT_CLARIF[Wait for Input]
    WAIT_CLARIF -->|User Response| REQ
    REQ -->|Success| PLAN[🗺️ Plan Agent]
    
    PLAN --> UXUI[🎨 UX/UI Agent]
    
    UXUI --> DESIGN_GATE{Approval Gate: DESIGN}
    DESIGN_GATE -->|UX Approval| CHECK_ARCH
    DESIGN_GATE -->|Arch Approval| CHECK_UX
    
    subgraph Approval Process
        CHECK_ARCH{Check Architect}
        CHECK_UX{Check UX}
    end
    
    DESIGN_GATE -->|All Approved| ARCH[🏗️ Architect Agent]
    
    ARCH --> CODE[💻 Code Agent]
    CODE -->|Git Commit| REFACTOR[♻️ Refactoring Agent]
    REFACTOR --> TEST[🧪 Test/QA Agent]
    
    TEST -->|Test Files Created| DOC[📝 Doc Agent]
    
    DOC -->|Push & PR| RELEASE[🚀 Release Agent]
    
    RELEASE --> RELEASE_GATE{Approval Gate: RELEASE}
    RELEASE_GATE -->|Approved| MONITOR[📊 Monitoring Agent]
    
    MONITOR -->|Restart Approval| EVAL[📈 Evaluation Agent]
    
    EVAL -->|Record Metrics| End((Finish))
    
    %% Feedback Loops
    style WAIT_CLARIF fill:#f9f,stroke:#333
    style DESIGN_GATE fill:#ff9,stroke:#333
    style RELEASE_GATE fill:#ff9,stroke:#333
    style EVAL fill:#9f9,stroke:#333
```

## Agent Summary (11 Agents)

| # | Agent | Role | Output | RAG |
|---|-------|------|--------|-----|
| 1 | REQUIREMENT | 요구사항 정제 | 명확한 요구사항 또는 질문 + `custom_path` 설정 | ✅ |
| 2 | PLAN | 로드맵/태스크 분해 | 프로젝트 계획 (기존 코드 기반) | ✅ |
| 3 | UXUI | UX/UI 설계 | 사용자 플로우, 디자인 시스템 | - |
| 4 | ARCHITECT | 아키텍처 설계 | 기술 스택, 디렉토리 구조 | - |
| 5 | CODE | 코드 구현 | 실제 코드 파일 (Git Commit) | ✅ |
| 6 | REFACTORING | 코드 리뷰 + 직접 수정 | 리팩토링된 코드 (Git Commit) | ✅ |
| 7 | TESTQA | 테스트 작성 | 테스트 코드 (Git Commit) | ✅ |
| 8 | DOC | 문서화 | README 등 (Git Commit + PR) | - |
| 9 | RELEASE | 배포 점검 | 릴리즈 노트 | - |
| 10 | MONITORING | 모니터링 설정 | 재시작 승인 요청 | - |
| 11 | EVALUATION | 성과 평가 | 성취도 점수, 개선점 | - |

## RAG Integration

에이전트들은 등록된 저장소의 코드를 ChromaDB에서 검색하여 프로젝트 이해도를 높입니다.

| Agent | RAG 용도 | top_k |
|-------|----------|-------|
| REQUIREMENT | 전체 구조 파악, target_repo 결정 | 5 |
| PLAN | 기존 코드 기반 태스크 분해 | 8 |
| CODE | 기존 코드 스타일/패턴 참조 | 10 |
| REFACTORING | 기존 패턴과 일관성 유지 | 8 |
| TESTQA | 기존 테스트 구조 참조 | 6 |

### 저장소 경로 전달
```
REQUIREMENT → target_repo + custom_path 설정
     ↓
CODE/REFACTORING/TESTQA/DOC → custom_path 사용하여 실제 저장소에서 작업
```
