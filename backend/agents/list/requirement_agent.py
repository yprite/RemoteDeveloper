from typing import Dict, Any, Optional, List
import os
import json
import logging
from agents.base import AgentStrategy
from core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
prompt_manager = PromptManager()

# Repository storage path
REPOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "repos")


def _get_rag_context(query: str, top_k: int = 5) -> str:
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
            content = r.get("content", "")[:500]  # Limit content size
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
        event_id = event.get("meta", {}).get("event_id", "unknown")
        prompt = event.get("task", {}).get("original_prompt", "")
        
        # Get registered repositories
        repos = _get_available_repos()
        repos_context = ""
        if repos:
            repos_list = [f"- {r['name']} ({r['url']})" for r in repos]
            repos_context = f"\n\n등록된 저장소:\n" + "\n".join(repos_list)
        
        # Query RAG for relevant code context
        rag_context = _get_rag_context(prompt)
        code_context = ""
        if rag_context:
            code_context = f"\n\n## 관련 코드 컨텍스트\n{rag_context}"
        
        # Build enhanced prompt
        enhanced_prompt = prompt + repos_context + code_context
        
        try:
            llm = self.get_llm_service()
            system_prompt = self.prompt_template.format(original_prompt=enhanced_prompt)
            response_text = llm.chat_completion(system_prompt, "요구사항을 분석해주세요.", json_mode=True)
            
            if not response_text:
                logger.error(f"[{self.name}] event={event_id} - LLM returned empty response")
                event["data"]["requirement"] = "[Error] LLM returned empty response"
                return event
            
            result = json.loads(response_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] event={event_id} - JSON decode failed: {e}")
            result = {"needs_clarification": False, "requirement_summary": response_text[:500] if response_text else ""}
        except Exception as e:
            logger.error(f"[{self.name}] event={event_id} - {type(e).__name__}: {e}")
            event["data"]["requirement"] = f"[Error] {str(e)}"
            return event

        # Handle clarification
        if result.get("needs_clarification"):
            event["task"]["needs_clarification"] = True
            event["task"]["clarification_question"] = result.get("clarification_question")
            output = f"[요구사항 분석 중] 추가 정보 필요: {result.get('clarification_question')}"
        else:
            event["task"]["needs_clarification"] = False
            event["task"]["clarification_question"] = None
            
            # Store additional analysis results
            if result.get("required_agents"):
                event["task"]["required_agents"] = result.get("required_agents")
            if result.get("skip_agents"):
                event["task"]["skip_agents"] = result.get("skip_agents")
            if result.get("target_repo"):
                repo_name = result.get("target_repo")
                # Find actual local path for the repository
                local_path = os.path.join(REPOS_DIR, repo_name)
                if os.path.exists(local_path):
                    event["task"]["git_context"] = {
                        "repo_name": repo_name,
                        "custom_path": local_path  # CODE agent will use this path
                    }
                    logger.info(f"[{self.name}] Set git_context: repo={repo_name}, path={local_path}")
                else:
                    # Fallback: repo not cloned yet
                    event["task"]["git_context"] = {"repo_name": repo_name}
                    logger.warning(f"[{self.name}] Repository path not found: {local_path}")
            
            output = f"[요구사항 정제 완료]\n{result.get('requirement_summary', '')}"
            
            # Add agent routing info if available
            if result.get("required_agents"):
                output += f"\n\n필요 에이전트: {', '.join(result.get('required_agents'))}"
        
        event["data"]["requirement"] = output
        return event
