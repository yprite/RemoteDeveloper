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
        
        # Call LLM expecting JSON mode for test files
        response = llm_service.chat_completion(formatted_prompt, "테스트 코드를 작성해주세요.", json_mode=True)
        
        try:
            data = json.loads(response)
            test_files = data.get("test_files", [])
            test_command = data.get("test_command", "pytest")
            
            # Git Operations
            repo_path = get_repo_path(event)
            git = GitService(repo_path)
            
            # Checkout existing task branch
            task_id = event.get("meta", {}).get("event_id", "task")
            if task_id.startswith("evt_"):
                 branch_name = f"feature/{task_id}"
            else:
                 branch_name = f"feature/task_{task_id}"

            try:
                git.checkout(branch_name) # Should already exist from CodeAgent
            except:
                logger.warning(f"Branch {branch_name} not found, staying on current.")

            # Write test files
            for file in test_files:
                git.write_file_content(file["path"], file["content"])
            
            # Commit tests
            if len(test_files) > 0:
                git.commit(f"test: Add {len(test_files)} test files")
            
            # TODO: Run tests via subprocess here and capture output
            # For now, we simulate execution or just leave it as created
            
            output = f"[테스트 생성 완료]\n- Files: {len(test_files)}\n- Command: {test_command}\n- Branch: {branch_name}"
            
        except json.JSONDecodeError:
             # Fallback if text only
             output = f"[테스트 가이드]\n{response[:500]}..."
        except Exception as e:
             output = f"[Error] Test generation failed: {str(e)}"
             logger.error(f"TestQA Agent failed: {e}")

        event["data"]["test_results"] = output
        return event
