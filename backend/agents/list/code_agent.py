from typing import Dict, Any, Optional, List
import os
import json
import logging
from agents.base import AgentStrategy
from core.prompt_manager import PromptManager
from core.git_service import GitService

logger = logging.getLogger("agents")
prompt_manager = PromptManager()


def _get_rag_context(query: str, repo_filter: Optional[str] = None, top_k: int = 10) -> str:
    """Query RAG service for relevant code context with optional repo filter."""
    try:
        from core.rag_service import get_rag_service
        rag = get_rag_service()
        results = rag.query(query, top_k=top_k, repo_filter=repo_filter)
        
        if not results:
            return ""
        
        context_parts = []
        for r in results:
            file_path = r.get("metadata", {}).get("file", "unknown")
            content = r.get("content", "")[:1000]  # Larger chunks for code context
            context_parts.append(f"### {file_path}\n```\n{content}\n```")
        
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.warning(f"RAG query failed: {e}")
        return ""


def get_repo_path(event: Dict[str, Any]) -> str:
    """Determine where to perform file operations."""
    task_git_context = event.get("task", {}).get("git_context")
    if task_git_context and task_git_context.get("custom_path"):
        return task_git_context["custom_path"]
    
    workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "workspace_tasks"))
    task_id = event.get("meta", {}).get("event_id", "default_task")
    repo_path = os.path.join(workspace_dir, task_id)
    return repo_path

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
        event_id = event.get("meta", {}).get("event_id", "unknown")
        arch = event["data"].get("architecture", "")
        plan = event["data"].get("plan", "")
        original_prompt = event.get("task", {}).get("original_prompt", "")
        
        # Get target repo for filtering RAG results
        target_repo = event.get("task", {}).get("git_context", {}).get("repo_name")
        
        # Query RAG for specific code patterns related to the task
        rag_context = _get_rag_context(original_prompt, repo_filter=target_repo, top_k=10)
        code_context = ""
        if rag_context:
            code_context = f"\n\n## 기존 코드 참조\n다음은 수정/확장해야 할 기존 코드입니다. 이 코드들의 스타일, 패턴, import 구조를 따라서 구현하세요.\n{rag_context}"
        
        logger.info(f"[{self.name}] event={event_id} - RAG context: {len(rag_context)} chars, repo_filter={target_repo}")
        
        # Enhance architecture with code context
        enhanced_arch = arch + code_context
        
        formatted_prompt = self.prompt_template.format(architecture=enhanced_arch, plan=plan)
        llm = self.get_llm_service()  # Uses configured adapter (Claude CLI by default)
        
        try:
            response = llm.chat_completion(formatted_prompt, "코드를 구현해주세요.", json_mode=True)
            
            # Defensive check for None or empty response
            if not response:
                logger.error(f"[{self.name}] event={event_id} - LLM returned empty response. Input: arch_len={len(arch)}, plan_len={len(plan)}")
                event["data"]["code"] = "[Error] LLM returned empty response"
                return event
            
            data = json.loads(response)
            
            # Defensive check for None after parsing
            if data is None:
                logger.error(f"[{self.name}] event={event_id} - JSON parsed to None. Response: {response[:200]}")
                event["data"]["code"] = "[Error] Invalid JSON response from LLM"
                return event
            
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
                logger.warning(f"[{self.name}] event={event_id} - Could not checkout branch {branch_name}")
            
            for file in files:
                git.write_file_content(file["path"], file["content"])
            
            git.commit(commit_msg)
            output = f"[코드 구현 완료]\n- Files: {len(files)}\n- Branch: {branch_name}\n- Commit: {commit_msg}"
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] event={event_id} - JSON decode failed: {e}. Response preview: {response[:300] if response else 'None'}")
            event["task"]["has_error"] = True
            event["task"]["error_message"] = f"Code Agent: LLM 응답을 파싱할 수 없습니다"
            output = f"[Error] Code Agent failed to parse JSON"
        except Exception as e:
            input_summary = f"arch_len={len(arch)}, plan_len={len(plan)}"
            logger.error(f"[{self.name}] event={event_id} - {type(e).__name__}: {e}. Input: {input_summary}")
            event["task"]["has_error"] = True
            event["task"]["error_message"] = f"Code Agent: {str(e)}"
            output = f"[Error] {str(e)}"

        event["data"]["code"] = output
        return event
