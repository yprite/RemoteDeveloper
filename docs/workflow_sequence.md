# Workflow Sequence Diagram

Visualizes the complete task lifecycle from user request to evaluation.

```mermaid
sequenceDiagram
    participant User
    participant Telegram
    participant n8n
    participant Backend
    participant Redis
    participant Agent
    participant GitHub
    participant Dashboard
    
    %% Ingest Phase
    User->>Telegram: Send Request Message
    Telegram->>n8n: Webhook Trigger
    n8n->>n8n: Refine Requirement (LLM)
    n8n->>Backend: POST /event/ingest
    Backend->>Redis: RPUSH queue:REQUIREMENT
    Backend-->>n8n: 200 OK
    n8n-->>Telegram: Reply "Processing Started"
    
    %% Agent Processing Phase
    loop 11 Agents Pipeline
        Agent->>Redis: LPOP queue:{CURRENT}
        Redis-->>Agent: Event Data
        
        alt CODE / TESTQA / DOC Agent
            Agent->>Agent: Generate Code (LLM)
            Agent->>GitHub: Write Files
            Agent->>GitHub: Git Commit
        end
        
        alt DOC Agent (Final Git Ops)
            Agent->>GitHub: Git Push
            Agent->>GitHub: gh pr create
            GitHub-->>Agent: PR URL
        end
        
        Agent->>Redis: RPUSH queue:{NEXT}
    end
    
    %% Evaluation Phase
    Agent->>Agent: EVALUATION Agent
    Agent->>Redis: Record Metrics
    Agent->>Dashboard: Update Stats Tab
    
    %% Monitoring & Restart
    Agent->>Telegram: "재시작 승인 필요"
    Agent->>Dashboard: Show in Pending Tab
    User->>Dashboard: Approve Restart
    Dashboard->>Backend: POST /system/restart
    Backend->>Backend: os.execl (Self-Restart)
```

## Phase Summary

| Phase | Description |
|-------|-------------|
| **Ingest** | Telegram → n8n → Backend → Redis Queue |
| **Processing** | 11 Agents process sequentially via Redis queues |
| **Git Ops** | CODE/TESTQA/DOC commit files, DOC creates PR |
| **Evaluation** | EVALUATION agent scores achievement |
| **Restart** | MONITORING requests approval, Backend self-restarts |
