import os
import subprocess
from abc import ABC, abstractmethod
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Union, Dict
from datetime import datetime
import logging
import json

app = FastAPI(title="AI Development Team Server")

# Log storage
logs = []

# --- System Logging Interceptor ---
class InMemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            status = "info"
            if level in ["warning"]: status = "pending"
            if level in ["error", "critical"]: status = "failed"
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "agent": "SYSTEM",
                "message": msg,
                "status": status
            }
            logs.append(entry)
            if len(logs) > 200:
                logs.pop(0)
        except Exception:
            self.handleError(record)

# Setup logging
log_handler = InMemoryLogHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
logging.getLogger().addHandler(log_handler)
logging.getLogger("uvicorn").addHandler(log_handler)
logging.getLogger("uvicorn.access").addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# STRATEGY PATTERN: Agent Definitions
# =============================================================================

class AgentStrategy(ABC):
    """Abstract base class for all agents using Strategy Pattern."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name (used for queue name)."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human readable agent name."""
        pass
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """System prompt template for this agent."""
        pass
    
    @property
    @abstractmethod
    def next_agent(self) -> Optional[str]:
        """Next agent in the pipeline, None if last."""
        pass
    
    @abstractmethod
    def process(self, event: dict) -> dict:
        """Process event and return updated event with output."""
        pass
    
    def get_data_key(self) -> str:
        """Key to store output in event['data']."""
        return self.name.lower()


# --- 1. Requirement Refinement Agent ---
class RequirementAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "REQUIREMENT"
    
    @property
    def display_name(self) -> str:
        return "요구사항 정제 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 요구사항 정제 전문가입니다.
사용자의 아이디어를 구체화하고 명확한 요구사항으로 정제합니다.
부족한 정보가 있다면 질문을 통해 보완합니다.

다음 정보가 필요합니다:
- 프로젝트의 목적
- 주요 기능 목록
- 타겟 사용자
- 기술적 제약사항
- 우선순위

입력: {original_prompt}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "PLAN"
    
    def process(self, event: dict) -> dict:
        """Special handling: can request clarification from user."""
        prompt = event.get("task", {}).get("original_prompt", "")
        
        # Mock: Simple heuristic - if prompt is too short, ask for clarification
        if len(prompt) < 20:
            event["task"]["needs_clarification"] = True
            event["task"]["clarification_question"] = "프로젝트의 구체적인 목표와 주요 기능을 알려주세요."
            output = f"[요구사항 분석 중] 추가 정보 필요: '{prompt}'"
        else:
            event["task"]["needs_clarification"] = False
            event["task"]["clarification_question"] = None
            output = f"""[요구사항 정제 완료]
원본: {prompt}
정제된 요구사항:
- 목적: {prompt}에 대한 구현
- 기능: 핵심 기능 구현 예정
- 사용자: 일반 사용자
- 제약사항: 없음
"""
        
        event["data"]["requirement"] = output
        return event


# --- 2. Plan Agent ---
class PlanAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "PLAN"
    
    @property
    def display_name(self) -> str:
        return "PLAN 에이전트 (로드맵/태스크 분해)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 프로젝트 기획 전문가입니다.
요구사항을 바탕으로 로드맵을 작성하고 태스크를 분해합니다.

출력 형식:
- 마일스톤 정의
- 태스크 분해
- 의존성 파악
- 일정 추정

요구사항: {requirement}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "UXUI"
    
    def process(self, event: dict) -> dict:
        requirement = event.get("data", {}).get("requirement", "없음")
        output = f"""[프로젝트 계획]
마일스톤 1: 설계 단계 (1주)
  - Task 1.1: 요구사항 분석
  - Task 1.2: 기술 스택 결정
마일스톤 2: 구현 단계 (2주)
  - Task 2.1: 핵심 기능 개발
  - Task 2.2: UI 개발
마일스톤 3: 테스트 단계 (1주)
  - Task 3.1: 단위 테스트
  - Task 3.2: 통합 테스트
"""
        event["data"]["plan"] = output
        return event


# --- 3. UX/UI Agent ---
class UxUiAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "UXUI"
    
    @property
    def display_name(self) -> str:
        return "UX/UI 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 UX/UI 디자인 전문가입니다.
사용자 경험과 인터페이스를 설계합니다.

고려사항:
- 사용자 플로우
- 와이어프레임
- 디자인 시스템
- 접근성

계획: {plan}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "ARCHITECT"
    
    def process(self, event: dict) -> dict:
        output = """[UX/UI 설계]
사용자 플로우:
  1. 메인 화면 진입
  2. 기능 선택
  3. 작업 수행
  4. 결과 확인

디자인 시스템:
  - 색상: Primary #3B82F6, Secondary #10B981
  - 폰트: Inter, 시스템 폰트
  - 컴포넌트: 버튼, 카드, 모달
"""
        event["data"]["ux_ui"] = output
        return event


# --- 4. Architect Agent ---
class ArchitectAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "ARCHITECT"
    
    @property
    def display_name(self) -> str:
        return "ARCHITECT 에이전트 (구현 방식/설계 결정)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 소프트웨어 아키텍트입니다.
시스템 구조와 기술적 설계를 결정합니다.

결정사항:
- 아키텍처 패턴
- 기술 스택
- 데이터 모델
- API 설계
- 보안 고려사항

UX/UI 설계: {ux_ui}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "CODE"
    
    def process(self, event: dict) -> dict:
        output = """[아키텍처 설계]
패턴: Clean Architecture
구조:
  - Presentation Layer (React/Vue)
  - Application Layer (FastAPI)
  - Domain Layer (Business Logic)
  - Infrastructure Layer (PostgreSQL, Redis)

API 설계:
  - REST API with OpenAPI 3.0
  - JWT Authentication
"""
        event["data"]["architecture"] = output
        return event


# --- 5. Code Agent ---
class CodeAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "CODE"
    
    @property
    def display_name(self) -> str:
        return "CODE 에이전트 (구현)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 시니어 개발자입니다.
설계에 따라 코드를 구현합니다.

원칙:
- Clean Code
- SOLID 원칙
- 테스트 가능한 코드
- 적절한 주석

아키텍처: {architecture}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "REFACTORING"
    
    def process(self, event: dict) -> dict:
        output = """[코드 구현]
# main.py
def main():
    app = Application()
    app.initialize()
    app.run()

# models.py
class Entity:
    def __init__(self, id: str):
        self.id = id

# 구현 완료: 3개 파일, 150 LOC
"""
        event["data"]["code"] = output
        return event


# --- 6. Refactoring Agent ---
class RefactoringAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "REFACTORING"
    
    @property
    def display_name(self) -> str:
        return "Refactoring 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 리팩토링 전문가입니다.
코드 품질을 개선하고 기술 부채를 줄입니다.

점검 항목:
- 코드 중복 제거
- 명명 규칙 개선
- 복잡도 감소
- 성능 최적화

코드: {code}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "TESTQA"
    
    def process(self, event: dict) -> dict:
        output = """[리팩토링 결과]
개선 사항:
  - 중복 코드 3개 제거
  - 함수 분리: 2개 함수 → 5개 함수
  - 변수명 개선: 10개
  - Cyclomatic Complexity: 15 → 8

코드 품질 점수: B+ → A-
"""
        event["data"]["refactoring"] = output
        return event


# --- 7. Test/QA Agent ---
class TestQaAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "TESTQA"
    
    @property
    def display_name(self) -> str:
        return "TEST/QA 에이전트 (테스트/검증)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 QA 엔지니어입니다.
코드의 품질과 기능을 검증합니다.

테스트 종류:
- 단위 테스트
- 통합 테스트
- E2E 테스트
- 성능 테스트

리팩토링된 코드: {refactoring}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "DOC"
    
    def process(self, event: dict) -> dict:
        output = """[테스트 결과]
단위 테스트: 45/45 통과 (100%)
통합 테스트: 12/12 통과 (100%)
E2E 테스트: 5/5 통과 (100%)
코드 커버리지: 87%

성능 테스트:
  - 응답 시간: 평균 45ms
  - 처리량: 1000 req/s
"""
        event["data"]["test_results"] = output
        return event


# --- 8. Doc Agent ---
class DocAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "DOC"
    
    @property
    def display_name(self) -> str:
        return "DOC 에이전트 (문서)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 기술 문서 작성 전문가입니다.
프로젝트 문서를 작성합니다.

문서 유형:
- README
- API 문서
- 사용자 가이드
- 개발자 가이드

테스트 결과: {test_results}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "RELEASE"
    
    def process(self, event: dict) -> dict:
        output = """[문서화 완료]
생성된 문서:
  - README.md (설치 및 실행 가이드)
  - API.md (API 레퍼런스)
  - CONTRIBUTING.md (기여 가이드)
  - CHANGELOG.md (변경 이력)

API 문서: OpenAPI 3.0 스펙 생성 완료
"""
        event["data"]["documentation"] = output
        return event


# --- 9. Release Agent ---
class ReleaseAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "RELEASE"
    
    @property
    def display_name(self) -> str:
        return "Release 에이전트 (배포)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 DevOps 엔지니어입니다.
애플리케이션 배포를 담당합니다.

배포 단계:
- 빌드
- 스테이징 배포
- 프로덕션 배포
- 롤백 계획

문서: {documentation}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "MONITORING"
    
    def process(self, event: dict) -> dict:
        output = """[배포 완료]
빌드: v1.0.0-build.123
스테이징: https://staging.example.com ✓
프로덕션: https://app.example.com ✓

배포 정보:
  - Docker 이미지: app:v1.0.0
  - 배포 시간: 2분 30초
  - 헬스체크: 통과
"""
        event["data"]["release"] = output
        return event


# --- 10. Monitoring Agent ---
class MonitoringAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "MONITORING"
    
    @property
    def display_name(self) -> str:
        return "Monitoring 에이전트 (감시 및 VOC 수집)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 운영 모니터링 전문가입니다.
시스템 상태를 감시하고 사용자 피드백을 수집합니다.

모니터링 항목:
- 시스템 메트릭
- 에러 로그
- 사용자 피드백 (VOC)
- 성능 지표

배포 정보: {release}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return None  # End of pipeline
    
    def process(self, event: dict) -> dict:
        output = """[모니터링 설정 완료]
대시보드: https://monitor.example.com

알림 설정:
  - CPU > 80%: Slack 알림
  - 에러율 > 1%: PagerDuty 알림
  - 응답시간 > 500ms: 경고

VOC 수집 채널:
  - 인앱 피드백
  - 이메일
  - 고객센터 연동
"""
        event["data"]["monitoring"] = output
        return event


# =============================================================================
# AGENT REGISTRY
# =============================================================================

AGENT_REGISTRY: Dict[str, AgentStrategy] = {
    "REQUIREMENT": RequirementAgent(),
    "PLAN": PlanAgent(),
    "UXUI": UxUiAgent(),
    "ARCHITECT": ArchitectAgent(),
    "CODE": CodeAgent(),
    "REFACTORING": RefactoringAgent(),
    "TESTQA": TestQaAgent(),
    "DOC": DocAgent(),
    "RELEASE": ReleaseAgent(),
    "MONITORING": MonitoringAgent(),
}

AGENT_ORDER = [
    "REQUIREMENT", "PLAN", "UXUI", "ARCHITECT", "CODE",
    "REFACTORING", "TESTQA", "DOC", "RELEASE", "MONITORING"
]

# =============================================================================
# REDIS CONNECTION
# =============================================================================

import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print("[REDIS] Connected successfully")
except Exception as e:
    print(f"[REDIS] Connection failed: {e}")
    r = None

def add_log(agent: str, message: str, status: str = "info"):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "message": message,
        "status": status
    }
    logs.append(entry)
    if len(logs) > 200:
        logs.pop(0)

def push_event(queue_name: str, event: dict):
    if r:
        r.rpush(queue_name, json.dumps(event))
        add_log("SYSTEM", f"Pushed event to {queue_name}", "info")
    else:
        add_log("SYSTEM", "Redis not available", "failed")

def pop_event(queue_name: str) -> Optional[dict]:
    if r:
        item = r.lpop(queue_name)
        if item:
            return json.loads(item)
    return None

# =============================================================================
# API MODELS
# =============================================================================

class FileWriteRequest(BaseModel):
    path: str
    content: str

class CommandRequest(BaseModel):
    command: str
    cwd: Optional[str] = None

class QueueRequest(BaseModel):
    task: Union[dict, str]
    context: Optional[Union[dict, str]] = {}

class ClarificationResponse(BaseModel):
    event_id: str
    response: str

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
def health_check():
    return {"status": "active", "service": "ai-dev-team-server", "agents": len(AGENT_REGISTRY)}

@app.get("/agent/logs")
def get_agent_logs():
    return {"logs": logs}

@app.get("/agents")
def list_agents():
    """List all available agents with their info."""
    return {
        "agents": [
            {
                "name": agent.name,
                "display_name": agent.display_name,
                "queue": f"queue:{agent.name}",
                "next_agent": agent.next_agent
            }
            for agent in AGENT_REGISTRY.values()
        ],
        "order": AGENT_ORDER
    }

@app.post("/event/ingest")
def event_ingest(request: QueueRequest):
    """Ingress: Receives task and pushes to queue:REQUIREMENT (first agent)."""
    event_id = f"evt_{int(datetime.now().timestamp())}"
    
    if isinstance(request.task, str):
        task_data = {
            "title": f"Task-{event_id[-6:]}",
            "type": "CODE_ORCHESTRATION",
            "status": "PENDING",
            "current_stage": "REQUIREMENT",
            "original_prompt": request.task,
            "needs_clarification": False,
            "clarification_question": None,
            "git_context": None
        }
    else:
        task_data = request.task
        task_data["current_stage"] = "REQUIREMENT"
        task_data["needs_clarification"] = False
        task_data["clarification_question"] = None

    context_data = request.context
    if isinstance(context_data, str):
        try:
            context_data = json.loads(context_data)
        except:
            context_data = {"raw_parsing_error": str(context_data)}
    
    if context_data is None:
        context_data = {}

    event = {
        "meta": {
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "source": "api_ingress",
            "version": "1.0"
        },
        "context": context_data,
        "task": task_data,
        "data": {
            "requirement": None,
            "plan": None,
            "ux_ui": None,
            "architecture": None,
            "code": None,
            "refactoring": None,
            "test_results": None,
            "documentation": None,
            "release": None,
            "monitoring": None,
            "artifacts": []
        },
        "history": [{
            "stage": "INGRESS",
            "timestamp": datetime.now().isoformat(),
            "message": "Task ingested via API"
        }]
    }
    
    push_event("queue:REQUIREMENT", event)
    add_log("INGRESS", f"Ingested task: {event_id}", "success")
    return {"status": "queued", "event_id": event_id, "queue": "queue:REQUIREMENT"}

@app.post("/event/clarify")
def event_clarify(request: ClarificationResponse):
    """Handle user's clarification response for RequirementAgent."""
    # Find the event in requirement queue or waiting area
    if not r:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    # For simplicity, we'll look in a waiting queue
    waiting_key = f"waiting:clarification:{request.event_id}"
    event_json = r.get(waiting_key)
    
    if not event_json:
        raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found in waiting")
    
    event = json.loads(event_json)
    
    # Append clarification to the original prompt
    original = event["task"].get("original_prompt", "")
    event["task"]["original_prompt"] = f"{original}\n\n[사용자 추가 정보]: {request.response}"
    event["task"]["needs_clarification"] = False
    event["task"]["clarification_question"] = None
    
    # Add to history
    event["history"].append({
        "stage": "CLARIFICATION",
        "timestamp": datetime.now().isoformat(),
        "message": f"User provided clarification: {request.response[:50]}..."
    })
    
    # Remove from waiting and push back to requirement queue
    r.delete(waiting_key)
    push_event("queue:REQUIREMENT", event)
    
    add_log("CLARIFICATION", f"Clarification received for {request.event_id}", "success")
    return {"status": "clarification_received", "event_id": request.event_id}

@app.post("/agent/{agent_name}/process")
def agent_process(agent_name: str):
    """Worker: Picks 1 item from queue:{agent_name}, processes it, pushes to next queue."""
    agent_key = agent_name.upper()
    
    if agent_key not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    agent = AGENT_REGISTRY[agent_key]
    queue_name = f"queue:{agent_key}"
    event = pop_event(queue_name)
    
    if not event:
        return {"status": "empty", "message": f"No events in {queue_name}"}

    event_id = event['meta']['event_id']
    add_log(agent_key, f"Processing event {event_id}", "running")
    
    # Process using agent strategy
    event = agent.process(event)
    
    # Special handling for RequirementAgent: check if clarification needed
    if agent_key == "REQUIREMENT" and event["task"].get("needs_clarification"):
        # Store in waiting area instead of next queue
        waiting_key = f"waiting:clarification:{event_id}"
        if r:
            r.set(waiting_key, json.dumps(event))
        
        add_log(agent_key, f"Waiting for clarification: {event_id}", "pending")
        
        return {
            "status": "needs_clarification",
            "event_id": event_id,
            "question": event["task"].get("clarification_question"),
            "agent": agent_key
        }
    
    # Update task status
    next_agent = agent.next_agent
    event["task"]["current_stage"] = next_agent if next_agent else "DONE"
    if not next_agent:
        event["task"]["status"] = "COMPLETED"
    
    # Update history
    output_data = event["data"].get(agent.get_data_key(), "")
    event["history"].append({
        "stage": agent_key,
        "timestamp": datetime.now().isoformat(),
        "message": f"Processed by {agent.display_name}",
        "output_summary": str(output_data)[:100] + "..."
    })
    
    # Push to next queue or finish
    if next_agent:
        next_queue = f"queue:{next_agent}"
        push_event(next_queue, event)
        msg = f"Completed. Next -> {next_agent}"
    else:
        msg = "Pipeline Completed."
        add_log("SYSTEM", f"Workflow Finished for {event_id}", "success")

    add_log(agent_key, msg, "success")
    
    return {
        "status": "processed",
        "agent": agent_key,
        "display_name": agent.display_name,
        "output": event["data"].get(agent.get_data_key(), ""),
        "next_queue": f"queue:{next_agent}" if next_agent else None
    }

@app.get("/queues")
def get_queues():
    """Get content of all active queues."""
    queues = {}
    target_queues = [f"queue:{name}" for name in AGENT_ORDER]
    
    if r:
        for q in target_queues:
            items = r.lrange(q, 0, -1)
            parsed_items = []
            for item in items:
                try:
                    parsed_items.append(json.loads(item))
                except:
                    parsed_items.append({"raw": item})
            queues[q] = {"count": len(parsed_items), "items": parsed_items}
        
        # Also check waiting clarifications
        waiting_keys = r.keys("waiting:clarification:*")
        waiting = {}
        for key in waiting_keys:
            event_json = r.get(key)
            if event_json:
                waiting[key] = json.loads(event_json)
        queues["waiting:clarification"] = {"count": len(waiting), "items": waiting}
    else:
        return {"error": "Redis not connected"}
        
    return {"queues": queues}

@app.post("/pipeline/run-all")
def run_pipeline():
    """Process one event through the entire pipeline (for testing)."""
    results = []
    
    for agent_name in AGENT_ORDER:
        result = agent_process(agent_name)
        results.append({"agent": agent_name, "result": result})
        
        # Stop if needs clarification or empty
        if result.get("status") in ["needs_clarification", "empty"]:
            break
    
    return {"pipeline_results": results}

# =============================================================================
# FILE & COMMAND ENDPOINTS (Keep existing functionality)
# =============================================================================

@app.get("/files/list")
def list_files(path: str = "."):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    return {"files": os.listdir(path)}

@app.post("/files/read")
def read_file(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(path, "r") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/write")
def write_file(request: FileWriteRequest):
    try:
        directory = os.path.dirname(request.path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(request.path, "w") as f:
            f.write(request.content)
        return {"status": "success", "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/command/run")
def run_command(request: CommandRequest):
    try:
        current_cwd = request.cwd or os.getcwd()
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=current_cwd,
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
