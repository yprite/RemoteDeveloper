"""
Agent Implementations Module - All 10 agent implementations.
Now integrated with Real LLM and Git capabilities.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

from .base import AgentStrategy
from core.llm import LLMService
from core.git_service import GitService

logger = logging.getLogger("agents")
llm_service = LLMService()

# Helper to format prompts safely
def format_prompt(template: str, data: Dict[str, Any]) -> str:
    # Get all keys from the data dict to safely format (ignoring missing ones with empty string or similar if needed)
    # For now, we assume the specific keys needed by the prompt are present in 'data' dictionary.
    # We might need to map event['data'] keys to prompt keys.
    try:
        return template.format(**data)
    except KeyError as e:
        logger.warning(f"Key missing in prompt formatting: {e}")
        return template # Fallback, might contain {key} literal

def get_repo_path(event: Dict[str, Any]) -> str:
    """Determine where to perform file operations."""
    task_git_context = event.get("task", {}).get("git_context")
    if task_git_context and task_git_context.get("custom_path"):
        return task_git_context["custom_path"]
    
    # Default to a workspace directory
    # For self-improvement, it might default to os.getcwd() but that's risky.
    # We'll use a specific 'workspace' dir relative to backend.
    
    workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "workspace_tasks"))
    task_id = event.get("meta", {}).get("event_id", "default_task")
    repo_path = os.path.join(workspace_dir, task_id)
    return repo_path

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

입력: {original_prompt}

판단 기준:
1. 요구사항이 명확하고 상세한가?
2. 기술적 제약사항이나 목표가 포함되어 있는가?

출력 형식:
만약 불명확하다면 JSON으로 출력:
{{
    "needs_clarification": true,
    "clarification_question": "사용자에게 물어볼 질문"
}}

명확하다면 JSON으로 출력:
{{
    "needs_clarification": false,
    "requirement_summary": "정제된 요구사항 텍스트"
}}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "PLAN"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        prompt = event.get("task", {}).get("original_prompt", "")
        
        # 1. LLM Call
        system_prompt = self.prompt_template.format(original_prompt=prompt)
        response_text = llm_service.chat_completion(system_prompt, "요구사항을 분석해주세요.", json_mode=True)
        
        try:
            result = json.loads(response_text)
        except:
            # Fallback if json parsing fails
            result = {"needs_clarification": False, "requirement_summary": response_text}

        if result.get("needs_clarification"):
            event["task"]["needs_clarification"] = True
            event["task"]["clarification_question"] = result.get("clarification_question")
            output = f"[요구사항 분석 중] 추가 정보 필요: {result.get('clarification_question')}"
        else:
            event["task"]["needs_clarification"] = False
            event["task"]["clarification_question"] = None
            output = f"[요구사항 정제 완료]\n{result.get('requirement_summary')}"
        
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

요구사항: {requirement}

출력 형식 (Markdown):
# 프로젝트 계획
## 마일스톤
...
## 태스크 상세
...
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "UXUI"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        req = event["data"].get("requirement", "")
        formatted_prompt = self.prompt_template.format(requirement=req)
        
        output = llm_service.chat_completion(formatted_prompt, "계획을 수립해주세요.")
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

계획: {plan}

출력 형식 (Markdown):
# UX/UI 디자인
## 사용자 플로우
...
## 디자인 시스템 제안
...
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "ARCHITECT"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        plan = event["data"].get("plan", "")
        formatted_prompt = self.prompt_template.format(plan=plan)
        
        output = llm_service.chat_completion(formatted_prompt, "UX/UI를 설계해주세요.")
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

UX/UI 설계: {ux_ui}

출력 형식 (Markdown):
# 아키텍처 설계
## 기술 스택
## 디렉토리 구조
## 데이터 모델
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "CODE"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        ux_ui = event["data"].get("ux_ui", "")
        formatted_prompt = self.prompt_template.format(ux_ui=ux_ui)
        
        output = llm_service.chat_completion(formatted_prompt, "아키텍처를 설계해주세요.")
        event["data"]["architecture"] = output
        return event


# --- 5. Code Agent ---
class CodeAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "CODE"
    
    @property
    def display_name(self) -> str:
        return "CODE 에이전트 (구현 및 Git 작업)"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 시니어 개발자입니다.
설계에 따라 전제 코드를 작성합니다.

아키텍처: {architecture}
계획: {plan}

**중요**: 반드시 아래 JSON 포맷으로 코드를 출력해야 합니다. 실제 파일 시스템에 작성될 것입니다.
{{
    "files": [
        {{
            "path": "backend/main.py",
            "content": "..."
        }},
        {{
            "path": "frontend/src/App.js",
            "content": "..."
        }}
    ],
    "commit_message": "feat: 구현 내용 요약"
}}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "REFACTORING"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        arch = event["data"].get("architecture", "")
        plan = event["data"].get("plan", "")
        
        formatted_prompt = self.prompt_template.format(architecture=arch, plan=plan)
        response = llm_service.chat_completion(formatted_prompt, "코드를 구현해주세요.", json_mode=True)
        
        try:
            data = json.loads(response)
            files = data.get("files", [])
            commit_msg = data.get("commit_message", "Implemented features")
            
            # Git Operations
            repo_path = get_repo_path(event)
            # If repo_path doesn't exist, we might need to clone.
            # For now, let's assume we are working in the specified path or create it.
            
            git = GitService(repo_path)
            # Check if we should clone from a URL provided in task
            repo_url = event.get("task", {}).get("git_context", {}).get("repo_url")
            
            if repo_url:
                 git.clone(repo_url)
            
            # Create a branch for this task
            task_id = event.get("meta", {}).get("event_id", "task")
            branch_name = f"feature/{task_id}"
            try:
                git.checkout(branch_name, create_if_missing=True)
            except:
                logger.warning(f"Could not checkout branch {branch_name}, continuing in current branch.")
            
            # Write files
            for file in files:
                git.write_file_content(file["path"], file["content"])
            
            # Commit
            git.commit(commit_msg)
            
            output = f"[코드 구현 완료]\n- Files: {len(files)}\n- Branch: {branch_name}\n- Commit: {commit_msg}"
            
        except json.JSONDecodeError:
            output = f"[Error] Code Agent failed to produce JSON:\n{response[:200]}..."
        except Exception as e:
             output = f"[Error] Git/File Operation failed: {str(e)}"
             logger.error(f"Code Agent failed: {e}")

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
코드 품질을 개선합니다.

현재는 자동화된 리팩토링보다, 코드 리뷰 코멘트를 남기는 것에 집중해주세요.
코드 구현 내역: {code}

출력: 리팩토링 제안 사항
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "TESTQA"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        code_summary = event["data"].get("code", "")
        formatted_prompt = self.prompt_template.format(code=code_summary)
        
        output = llm_service.chat_completion(formatted_prompt, "리팩토링 제안을 해주세요.")
        event["data"]["refactoring"] = output
        return event


# --- 7. Test/QA Agent ---
class TestQaAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "TESTQA"
    
    @property
    def display_name(self) -> str:
        return "TEST/QA 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """당신은 QA 엔지니어입니다.
현재 구현된 코드에 대한 테스트 전략을 수립해주세요.

구현 내역: {code}
출력: 테스트 시나리오 및 케이스
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "DOC"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # In a real scenario, this would run 'pytest' using GitService/Subprocess
        code_summary = event["data"].get("code", "")
        formatted_prompt = self.prompt_template.format(code=code_summary)
        
        output = llm_service.chat_completion(formatted_prompt, "테스트 시나리오를 작성해주세요.")
        event["data"]["test_results"] = output
        return event


# --- 8. Doc Agent ---
class DocAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "DOC"
    
    @property
    def display_name(self) -> str:
        return "DOC 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """프로젝트 문서를 작성해주세요.
        
내용:
{code}
{test_results}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "RELEASE"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        code = event["data"].get("code", "")
        test = event["data"].get("test_results", "")
        
        formatted_prompt = self.prompt_template.format(code=code, test_results=test)
        
        output = llm_service.chat_completion(formatted_prompt, "문서를 작성해주세요.")
        event["data"]["documentation"] = output
        return event


# --- 9. Release Agent ---
class ReleaseAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "RELEASE"
    
    @property
    def display_name(self) -> str:
        return "Release 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """배포 준비 상태를 점검해주세요.
        
문서: {documentation}
"""
    
    @property
    def next_agent(self) -> Optional[str]:
        return "MONITORING"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        doc = event["data"].get("documentation", "")
        formatted_prompt = self.prompt_template.format(documentation=doc)
        
        output = llm_service.chat_completion(formatted_prompt, "배포 체크리스트 확인.")
        event["data"]["release"] = output
        return event


# --- 10. Monitoring Agent ---
class MonitoringAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "MONITORING"
    
    @property
    def display_name(self) -> str:
        return "Monitoring 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return """모니터링 알림 규칙을 생성해주세요."""
    
    @property
    def next_agent(self) -> Optional[str]:
        return None
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        output = llm_service.chat_completion(self.prompt_template, "모니터링 설정을 제안해주세요.")
        event["data"]["monitoring"] = output
        return event
