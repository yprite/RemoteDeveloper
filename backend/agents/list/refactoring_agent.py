from typing import Dict, Any, Optional
import os
import json
import logging
from agents.base import AgentStrategy
from core.prompt_manager import PromptManager
from core.git_service import GitService
from core.github_service import get_github_service
from core.pr_wait_service import get_pr_wait_service

logger = logging.getLogger("agents")
prompt_manager = PromptManager()


def _get_rag_context(query: str, repo_filter: Optional[str] = None, top_k: int = 8) -> str:
    """Query RAG service for relevant code context."""
    try:
        from core.rag_service import get_rag_service
        rag = get_rag_service()
        results = rag.query(query, top_k=top_k, repo_filter=repo_filter)
        
        if not results:
            return ""
        
        context_parts = []
        for r in results:
            file_path = r.get("metadata", {}).get("file", "unknown")
            content = r.get("content", "")[:800]
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


class RefactoringAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "REFACTORING"
    
    @property
    def display_name(self) -> str:
        return "Refactoring 에이전트 (리팩토링 + PR)"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "TESTQA"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        code_summary = event["data"].get("code", "")
        original_prompt = event.get("task", {}).get("original_prompt", "")
        
        # Get target repo for filtering RAG results
        target_repo = event.get("task", {}).get("git_context", {}).get("repo_name")
        
        # Query RAG for related code patterns and existing implementations
        rag_context = _get_rag_context(original_prompt, repo_filter=target_repo, top_k=8)
        code_context = ""
        if rag_context:
            code_context = f"\n\n## 관련 기존 코드\n다음은 프로젝트의 기존 코드 패턴입니다. 리팩토링 시 이 패턴들과의 일관성을 고려하세요.\n{rag_context}"
        
        logger.info(f"[{self.name}] event={event_id} - RAG context: {len(rag_context)} chars")
        
        enhanced_code = code_summary + code_context
        formatted_prompt = self.prompt_template.format(code=enhanced_code)
        
        llm = self.get_llm_service()  # Uses configured adapter (Codex CLI by default)
        
        try:
            response = llm.chat_completion(formatted_prompt, "리팩토링을 수행해주세요.", json_mode=True)
            
            if not response:
                logger.error(f"[{self.name}] event={event_id} - LLM returned empty response")
                event["data"]["refactoring"] = "[Error] LLM returned empty response"
                return event
            
            data = json.loads(response)
            
            if data is None:
                logger.error(f"[{self.name}] event={event_id} - JSON parsed to None")
                event["data"]["refactoring"] = "[Error] Invalid JSON response"
                return event
            
            # Check if refactoring is needed
            needs_refactoring = data.get("needs_refactoring", False)
            quality_grade = data.get("quality_grade", "B")
            review_summary = data.get("review_summary", "")
            files = data.get("files", [])
            
            if not needs_refactoring or not files:
                # No refactoring needed - just report
                output = f"[코드 리뷰 완료]\n- 품질 등급: {quality_grade}\n- 리팩토링 필요: 없음\n\n{review_summary}"
                event["data"]["refactoring"] = output
                return event
            
            # Apply refactoring changes
            repo_path = get_repo_path(event)
            git = GitService(repo_path)
            repo_url = event.get("task", {}).get("git_context", {}).get("repo_url")
            
            # Branch naming: feature/evt_***@refactoring
            task_id = event.get("meta", {}).get("event_id", "task")
            if task_id.startswith("evt_"):
                branch_name = f"feature/{task_id}@refactoring"
            else:
                branch_name = f"feature/task_{task_id}@refactoring"
            
            try:
                # Checkout from main to get fresh branch
                git.checkout("main")
                git.checkout(branch_name, create_if_missing=True)
            except Exception as e:
                logger.warning(f"[{self.name}] event={event_id} - Branch checkout issue: {e}")
            
            # Write refactored files
            for file in files:
                git.write_file_content(file["path"], file["content"])
            
            # Commit refactoring changes
            commit_msg = data.get("commit_message", f"refactor: Code quality improvements ({quality_grade})")
            if len(files) > 0:
                git.commit(commit_msg)
            
            # Push and create PR
            pr_info = ""
            github = get_github_service()
            
            if repo_url:
                parts = repo_url.rstrip(".git").split("/")
                if len(parts) >= 2:
                    github.set_repo(parts[-2], parts[-1])
                    
                    if github.push_branch(repo_path, branch_name):
                        pr_title = f"[REFACTORING] {commit_msg}"
                        pr_body = f"""## 리팩토링 내용
- 품질 등급: {quality_grade}
- 수정된 파일: {len(files)}개

## 변경 파일
{chr(10).join([f"- {f['path']}" for f in files])}

## 리뷰 요약
{review_summary[:500]}

---
*Generated by REFACTORING Agent (event: {event_id})*
"""
                        pr = github.create_pull_request(
                            title=pr_title,
                            body=pr_body,
                            head=branch_name,
                            base="main"
                        )
                        if pr:
                            pr_info = f"\n- PR: #{pr['number']} ({pr['html_url']})"
                            event["data"]["refactoring_pr_number"] = pr["number"]
                            
                            # Register PR wait - block until merged
                            pr_wait = get_pr_wait_service()
                            pr_wait.register_pr_wait(
                                event_id=event_id,
                                pr_number=pr["number"],
                                repo_owner=parts[-2],
                                repo_name=parts[-1],
                                agent_name=self.name,
                                next_agent=self.next_agent or "TESTQA",
                                event_data=event
                            )
                            event["status"] = "PENDING_PR_CLOSE"
                            pr_info += "\n- Status: PENDING_PR_CLOSE"
            
            output = f"[리팩토링 완료]\n- 품질 등급: {quality_grade}\n- 수정된 파일: {len(files)}개\n- Branch: {branch_name}\n- Commit: {commit_msg}{pr_info}\n\n{review_summary}"
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] event={event_id} - JSON decode failed: {e}")
            # Fallback: treat as review-only response
            output = f"[코드 리뷰]\n{response[:1000] if response else 'No response'}..."
        except Exception as e:
            logger.error(f"[{self.name}] event={event_id} - {type(e).__name__}: {e}")
            output = f"[Error] {str(e)}"
        
        event["data"]["refactoring"] = output
        return event

