from typing import Dict, Any, Optional, List
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
        return "CODE 에이전트 (구현 + PR 생성)"
    
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
        
        # Check if this is a rework event
        is_rework = event.get("is_rework", False)
        rework_feedback = event.get("rework_feedback", "")
        
        if is_rework:
            logger.info(f"[{self.name}] event={event_id} - REWORK requested based on PR feedback")
        
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
        
        # Add rework feedback to prompt if this is a rework
        if is_rework and rework_feedback:
            enhanced_arch += f"\n\n## ⚠️ PR 리뷰 피드백 (수정 필요)\n{rework_feedback}\n\n위 피드백을 반영하여 코드를 수정해주세요."
        
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
            # Branch naming: feature/evt_***
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
            
            # Push and create PR
            pr_info = ""
            github = get_github_service()
            
            # Extract repo owner/name from URL
            if repo_url:
                parts = repo_url.rstrip(".git").split("/")
                if len(parts) >= 2:
                    github.set_repo(parts[-2], parts[-1])
                    
                    # Push branch
                    if github.push_branch(repo_path, branch_name):
                        # Create PR
                        pr_title = f"[CODE] {commit_msg}"
                        pr_body = f"""## 구현 내용
{original_prompt[:500]}

## 변경 파일
{chr(10).join([f"- {f['path']}" for f in files])}

## 커밋 메시지
{commit_msg}

---
*Generated by CODE Agent (event: {event_id})*
"""
                        pr = github.create_pull_request(
                            title=pr_title,
                            body=pr_body,
                            head=branch_name,
                            base="main"
                        )
                        if pr:
                            pr_info = f"\n- PR: #{pr['number']} ({pr['html_url']})"
                            event["data"]["pr_number"] = pr["number"]
                            event["data"]["pr_url"] = pr["html_url"]
                            
                            # Register PR wait - block until merged
                            pr_wait = get_pr_wait_service()
                            pr_wait.register_pr_wait(
                                event_id=event_id,
                                pr_number=pr["number"],
                                repo_owner=parts[-2],
                                repo_name=parts[-1],
                                agent_name=self.name,
                                next_agent=self.next_agent or "REFACTORING",
                                event_data=event
                            )
                            event["status"] = "PENDING_PR_CLOSE"
                            pr_info += "\n- Status: PENDING_PR_CLOSE (waiting for merge)"
            
            output = f"[코드 구현 완료]\n- Files: {len(files)}\n- Branch: {branch_name}\n- Commit: {commit_msg}{pr_info}"
            
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

