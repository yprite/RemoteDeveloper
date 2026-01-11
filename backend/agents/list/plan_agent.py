from typing import Dict, Any, Optional, List
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()


def _get_rag_context(query: str, top_k: int = 8) -> str:
    """Query RAG service for relevant code context."""
    try:
        from core.rag_service import get_rag_service
        rag = get_rag_service()
        results = rag.query(query, top_k=top_k)
        
        if not results:
            return ""
        
        context_parts = []
        for r in results:
            file_path = r.get("metadata", {}).get("file", "unknown")
            content = r.get("content", "")[:800]  # Limit content size
            context_parts.append(f"### {file_path}\n```\n{content}\n```")
        
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.warning(f"RAG query failed: {e}")
        return ""


def _get_available_repos() -> List[Dict]:
    """Get list of registered repositories."""
    try:
        from core.database import get_repositories
        return get_repositories(active_only=True)
    except Exception as e:
        logger.warning(f"Failed to get repos: {e}")
        return []


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
        event_id = event.get("meta", {}).get("event_id", "unknown")
        req = event["data"].get("requirement", "")
        original_prompt = event.get("task", {}).get("original_prompt", "")
        
        # Get target repo from task context (set by RequirementAgent)
        target_repo = event.get("task", {}).get("git_context", {}).get("repo_name", "")
        
        # Get registered repositories for context
        repos = _get_available_repos()
        repos_context = ""
        if repos:
            repos_list = [f"- {r['name']} ({r['url']})" for r in repos]
            repos_context = f"\n\n## 등록된 저장소\n" + "\n".join(repos_list)
            if target_repo:
                repos_context += f"\n\n**작업 대상 저장소**: {target_repo}"
        
        # Query RAG for relevant code context using original prompt
        rag_context = _get_rag_context(original_prompt)
        code_context = ""
        if rag_context:
            code_context = f"\n\n## 현재 프로젝트 코드 컨텍스트\n다음은 이 프로젝트에서 관련된 기존 코드입니다. 태스크 분해 시 이 코드들을 참고하여 기존 구현을 활용하거나 수정하는 방향으로 계획하세요.\n{rag_context}"
        
        # Build enhanced requirement with context
        enhanced_req = req + repos_context + code_context
        
        logger.info(f"[{self.name}] event={event_id} - RAG context: {len(rag_context)} chars, repos: {len(repos)}")
        
        formatted_prompt = self.prompt_template.format(requirement=enhanced_req)
        
        output = llm_service.chat_completion(formatted_prompt, "계획을 수립해주세요.")
        event["data"]["plan"] = output
        return event
