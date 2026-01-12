from typing import Dict, Any, Optional
import os
import json
import logging
import subprocess
from agents.base import AgentStrategy
from core.prompt_manager import PromptManager
from core.git_service import GitService
from core.github_service import get_github_service
from core.pr_wait_service import get_pr_wait_service

logger = logging.getLogger("agents")
prompt_manager = PromptManager()


def _get_rag_context(query: str, repo_filter: Optional[str] = None, top_k: int = 6) -> str:
    """Query RAG service for relevant test patterns and code."""
    try:
        from core.rag_service import get_rag_service
        rag = get_rag_service()
        
        # Search for existing test patterns
        test_query = f"test {query}"
        results = rag.query(test_query, top_k=top_k, repo_filter=repo_filter)
        
        if not results:
            return ""
        
        context_parts = []
        for r in results:
            file_path = r.get("metadata", {}).get("file", "unknown")
            content = r.get("content", "")[:600]
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


def _run_tests(repo_path: str, test_command: str) -> str:
    """Run tests and return the output."""
    try:
        result = subprocess.run(
            test_command.split(),
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300
        )
        output = result.stdout + result.stderr
        return output[:3000]  # Limit output size
    except Exception as e:
        return f"[Test execution failed: {e}]"


class TestQaAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "TESTQA"
    
    @property
    def display_name(self) -> str:
        return "TEST/QA 에이전트 (테스트 + PR + 결과)"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "DOC"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        code_summary = event["data"].get("code", "")
        original_prompt = event.get("task", {}).get("original_prompt", "")
        
        # Get target repo for filtering RAG results
        target_repo = event.get("task", {}).get("git_context", {}).get("repo_name")
        
        # Query RAG for existing test patterns in the project
        rag_context = _get_rag_context(original_prompt, repo_filter=target_repo, top_k=6)
        test_context = ""
        if rag_context:
            test_context = f"\n\n## 기존 테스트 패턴 참조\n다음은 프로젝트의 기존 테스트 코드입니다. 이 패턴과 구조를 따라서 테스트를 작성하세요.\n{rag_context}"
        
        logger.info(f"[{self.name}] event={event_id} - RAG context: {len(rag_context)} chars")
        
        enhanced_code = code_summary + test_context
        formatted_prompt = self.prompt_template.format(code=enhanced_code)
        
        try:
            llm = self.get_llm_service()
            response = llm.chat_completion(formatted_prompt, "테스트 코드를 작성해주세요.", json_mode=True)
            
            if not response:
                logger.error(f"[{self.name}] event={event_id} - LLM returned empty response. Input: code_len={len(code_summary)}")
                event["data"]["test_results"] = "[Error] LLM returned empty response"
                return event
            
            data = json.loads(response)
            
            if data is None:
                logger.error(f"[{self.name}] event={event_id} - JSON parsed to None. Response: {response[:200]}")
                event["data"]["test_results"] = "[Error] Invalid JSON response"
                return event
            
            test_files = data.get("test_files", [])
            test_command = data.get("test_command", "pytest")
            
            # Git Operations
            repo_path = get_repo_path(event)
            git = GitService(repo_path)
            repo_url = event.get("task", {}).get("git_context", {}).get("repo_url")
            
            # Branch naming: feature/evt_***@test
            task_id = event.get("meta", {}).get("event_id", "task")
            if task_id.startswith("evt_"):
                branch_name = f"feature/{task_id}@test"
            else:
                branch_name = f"feature/task_{task_id}@test"

            try:
                # Checkout from main to get fresh branch
                git.checkout("main")
                git.checkout(branch_name, create_if_missing=True)
            except Exception as e:
                logger.warning(f"[{self.name}] event={event_id} - Branch checkout issue: {e}")

            # Write test files
            for file in test_files:
                git.write_file_content(file["path"], file["content"])
            
            # Commit tests
            commit_msg = f"test: Add {len(test_files)} test files"
            if len(test_files) > 0:
                git.commit(commit_msg)
            
            # Run tests and capture output
            test_output = _run_tests(repo_path, test_command)
            
            # Push and create PR with test results
            pr_info = ""
            github = get_github_service()
            
            if repo_url:
                parts = repo_url.rstrip(".git").split("/")
                if len(parts) >= 2:
                    github.set_repo(parts[-2], parts[-1])
                    
                    if github.push_branch(repo_path, branch_name):
                        pr_title = f"[TESTQA] {commit_msg}"
                        pr_body = f"""## 테스트 내용
- 테스트 파일: {len(test_files)}개
- 테스트 명령: `{test_command}`

## 변경 파일
{chr(10).join([f"- {f['path']}" for f in test_files])}

## 테스트 결과
```
{test_output[:2000]}
```

---
*Generated by TESTQA Agent (event: {event_id})*
"""
                        pr = github.create_pull_request(
                            title=pr_title,
                            body=pr_body,
                            head=branch_name,
                            base="main"
                        )
                        if pr:
                            pr_info = f"\n- PR: #{pr['number']} ({pr['html_url']})"
                            event["data"]["test_pr_number"] = pr["number"]
                            
                            # Register PR wait - block until merged
                            pr_wait = get_pr_wait_service()
                            pr_wait.register_pr_wait(
                                event_id=event_id,
                                pr_number=pr["number"],
                                repo_owner=parts[-2],
                                repo_name=parts[-1],
                                agent_name=self.name,
                                next_agent=self.next_agent or "DOC",
                                event_data=event
                            )
                            event["status"] = "PENDING_PR_CLOSE"
                            pr_info += "\n- Status: PENDING_PR_CLOSE"
            
            output = f"[테스트 생성 완료]\n- Files: {len(test_files)}\n- Command: {test_command}\n- Branch: {branch_name}{pr_info}\n\n## 테스트 결과\n{test_output[:500]}..."
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] event={event_id} - JSON decode failed: {e}. Response: {response[:300] if response else 'None'}")
            output = f"[테스트 가이드]\n{response[:500] if response else 'No response'}..."
        except Exception as e:
            logger.error(f"[{self.name}] event={event_id} - {type(e).__name__}: {e}. Input: code_len={len(code_summary)}")
            output = f"[Error] {str(e)}"

        event["data"]["test_results"] = output
        return event

