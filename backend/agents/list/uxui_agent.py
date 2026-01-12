from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager
from core.mcp_client import get_mcp_client

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()


class UxUiAgent(AgentStrategy):
    """
    UX/UI Agent - Design user interface using best practices.
    
    Uses mcp-ux-rag for:
    - Shadcn/ui components
    - Tailwind CSS utilities
    - Radix UI primitives
    - Material Design guidelines
    - Nielsen Norman Group (NNG) principles
    - Apple Human Interface Guidelines (HIG)
    """
    
    @property
    def name(self) -> str:
        return "UXUI"
    
    @property
    def display_name(self) -> str:
        return "UX/UI 에이전트 (MCP-RAG)"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "ARCHITECT"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        plan = event["data"].get("plan", "")
        original_prompt = event.get("task", {}).get("original_prompt", "")
        
        # Extract repo name for context-aware queries
        repo_name = event.get("task", {}).get("git_context", {}).get("repo_name")
        
        # Query mcp-ux-rag for relevant design patterns + repo context
        mcp = get_mcp_client()
        ux_context = ""
        
        if mcp.is_server_available("mcp-ux-rag"):
            # Get relevant patterns + repo code
            results = mcp.query("mcp-ux-rag", original_prompt, top_k=5, repo_filter=repo_name)
            if results:
                pattern_texts = []
                for r in results:
                    pattern_texts.append(f"### {r['category']}\n{r['content']}")
                ux_context = "\n\n".join(pattern_texts)
            
            # Get specific recommendations with repo context
            recommendations = mcp.get_recommendations("mcp-ux-rag", original_prompt, repo_filter=repo_name)
            if recommendations:
                ux_context += f"\n\n## 디자인 권장사항\n{recommendations}"
            
            logger.info(f"[{self.name}] event={event_id} - MCP UX context: {len(ux_context)} chars, repo={repo_name}")
        else:
            logger.warning(f"[{self.name}] event={event_id} - mcp-ux-rag not available, using LLM only")
        
        # Enhance plan with UX patterns
        enhanced_plan = plan
        if ux_context:
            enhanced_plan = f"{plan}\n\n## UX/UI 디자인 패턴 참조\n다음은 적용해야 할 디자인 패턴과 원칙입니다:\n{ux_context}"
        
        formatted_prompt = self.prompt_template.format(plan=enhanced_plan)
        
        output = llm_service.chat_completion(formatted_prompt, "UX/UI를 설계해주세요.")
        event["data"]["ux_ui"] = output
        return event

