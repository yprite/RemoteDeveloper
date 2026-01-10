from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

class ArchitectAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "ARCHITECT"
    
    @property
    def display_name(self) -> str:
        return "ARCHITECT 에이전트 (구현 방식/설계 결정)"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "CODE"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        ux_ui = event["data"].get("ux_ui", "")
        formatted_prompt = self.prompt_template.format(ux_ui=ux_ui)
        
        output = llm_service.chat_completion(formatted_prompt, "아키텍처를 설계해주세요.")
        event["data"]["architecture"] = output
        return event
