from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

class UxUiAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "UXUI"
    
    @property
    def display_name(self) -> str:
        return "UX/UI 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "ARCHITECT"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        plan = event["data"].get("plan", "")
        formatted_prompt = self.prompt_template.format(plan=plan)
        
        output = llm_service.chat_completion(formatted_prompt, "UX/UI를 설계해주세요.")
        event["data"]["ux_ui"] = output
        return event
