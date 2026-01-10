"""
Agent Implementations Module - All 10 agent implementations.
Now integrated with Real LLM, Git capabilities, and YAML Prompt Management.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

from .base import AgentStrategy
from core.llm import LLMService
from core.git_service import GitService
from core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager() # Singleton instance

# Helper to format prompts safely
def format_prompt(template: str, data: Dict[str, Any]) -> str:
    try:
        return template.format(**data)
    except KeyError as e:
        logger.warning(f"Key missing in prompt formatting: {e}")
        return template 

def get_repo_path(event: Dict[str, Any]) -> str:
    """Determine where to perform file operations."""
    task_git_context = event.get("task", {}).get("git_context")
    if task_git_context and task_git_context.get("custom_path"):
        return task_git_context["custom_path"]
    
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
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
            git = GitService(repo_path)
            
            repo_url = event.get("task", {}).get("git_context", {}).get("repo_url")
            if repo_url:
                 git.clone(repo_url)
            
            task_id = event.get("meta", {}).get("event_id", "task")
            # Sanitize branch name
            if task_id.startswith("evt_"):
                 branch_name = f"feature/{task_id}"
            else:
                 branch_name = f"feature/task_{task_id}"

            try:
                git.checkout(branch_name, create_if_missing=True)
            except:
                logger.warning(f"Could not checkout branch {branch_name}, continuing in current branch.")
            
            for file in files:
                git.write_file_content(file["path"], file["content"])
            
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "DOC"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
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
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return None
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        output = llm_service.chat_completion(self.prompt_template, "모니터링 설정을 제안해주세요.")
        event["data"]["monitoring"] = output
        return event
