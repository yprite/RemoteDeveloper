from typing import Dict, Any, Optional
import os
import json
import logging
from ..base import AgentStrategy
from ...core.llm import LLMService
from ...core.prompt_manager import PromptManager
from ...core.git_service import GitService

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

def get_repo_path(event: Dict[str, Any]) -> str:
    """Determine where to perform file operations."""
    task_git_context = event.get("task", {}).get("git_context")
    if task_git_context and task_git_context.get("custom_path"):
        return task_git_context["custom_path"]
    
    workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "workspace_tasks"))
    task_id = event.get("meta", {}).get("event_id", "default_task")
    repo_path = os.path.join(workspace_dir, task_id)
    return repo_path

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
        
        response = llm_service.chat_completion(formatted_prompt, "문서를 작성해주세요.", json_mode=True)
        
        try:
            data = json.loads(response)
            files = data.get("files", [])
            
            # Git Operations
            repo_path = get_repo_path(event)
            git = GitService(repo_path)
            
            task_id = event.get("meta", {}).get("event_id", "task")
            if task_id.startswith("evt_"):
                 branch_name = f"feature/{task_id}"
            else:
                 branch_name = f"feature/task_{task_id}"

            try:
                git.checkout(branch_name)
            except:
                pass # Already on branch hopefully

            # Write doc files
            for file in files:
                git.write_file_content(file["path"], file["content"])
            
            # Commit docs
            if len(files) > 0:
                git.commit(f"docs: Add {len(files)} documentation files")
            
            output = f"[문서화 완료]\n- Files: {len(files)} (README etc.)\n- Branch: {branch_name}"
            
        except json.JSONDecodeError:
             output = f"[문서 초안]\n{response[:500]}..."
        except Exception as e:
             output = f"[Error] Doc generation failed: {str(e)}"
             logger.error(f"Doc Agent failed: {e}")

        event["data"]["documentation"] = output
        return event
