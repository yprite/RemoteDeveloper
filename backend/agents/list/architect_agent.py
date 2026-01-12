from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager
from core.mcp_client import get_mcp_client

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()


class ArchitectAgent(AgentStrategy):
    """
    ARCHITECT Agent - Design software architecture using best practices.
    
    Uses mcp-arch-rag for:
    - Clean Architecture
    - Domain-Driven Design (DDD)
    - Event-driven patterns
    - Saga / CQRS / Outbox
    - AWS Well-Architected Framework
    - Microservices patterns
    - Distributed system patterns
    """
    
    @property
    def name(self) -> str:
        return "ARCHITECT"
    
    @property
    def display_name(self) -> str:
        return "ARCHITECT 에이전트 (MCP-RAG)"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "CODE"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        ux_ui = event["data"].get("ux_ui", "")
        original_prompt = event.get("task", {}).get("original_prompt", "")
        
        # Extract repo name for context-aware queries
        repo_name = event.get("task", {}).get("git_context", {}).get("repo_name")
        
        # Query mcp-arch-rag for relevant architecture patterns + repo context
        mcp = get_mcp_client()
        arch_context = ""
        
        if mcp.is_server_available("mcp-arch-rag"):
            # Get relevant patterns + repo code
            results = mcp.query("mcp-arch-rag", original_prompt, top_k=5, repo_filter=repo_name)
            if results:
                pattern_texts = []
                for r in results:
                    pattern_texts.append(f"### {r['category']}\n{r['content']}")
                arch_context = "\n\n".join(pattern_texts)
            
            # Get specific recommendations with repo context
            recommendations = mcp.get_recommendations("mcp-arch-rag", original_prompt, repo_filter=repo_name)
            if recommendations:
                arch_context += f"\n\n## 아키텍처 권장사항\n{recommendations}"
            
            logger.info(f"[{self.name}] event={event_id} - MCP Arch context: {len(arch_context)} chars, repo={repo_name}")
        else:
            logger.warning(f"[{self.name}] event={event_id} - mcp-arch-rag not available, using LLM only")
        
        # Enhance UX/UI with architecture patterns
        enhanced_ux_ui = ux_ui
        if arch_context:
            enhanced_ux_ui = f"{ux_ui}\n\n## 아키텍처 패턴 참조\n다음은 적용해야 할 아키텍처 패턴과 원칙입니다:\n{arch_context}"
        
        formatted_prompt = self.prompt_template.format(ux_ui=enhanced_ux_ui)
        
        output = llm_service.chat_completion(formatted_prompt, "아키텍처를 설계해주세요.")
        event["data"]["architecture"] = output
        return event

