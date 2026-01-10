"""
Agent Implementations Module - All 10 agent implementations.
"""
from typing import Optional, Dict, Any

from .base import AgentStrategy


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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Special handling: can request clarification from user."""
        prompt = event.get("task", {}).get("original_prompt", "")
        
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        output = """[프로젝트 계획]
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
