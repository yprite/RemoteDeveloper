from typing import Dict, Any, Optional
import logging
from ..base import AgentStrategy
from ...core.llm import LLMService
from ...core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

class ReleaseAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "RELEASE"
    
    @property
    def display_name(self) -> str:
        return "Release 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "MONITORING"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        doc = event["data"].get("documentation", "")
        formatted_prompt = self.prompt_template.format(documentation=doc)
        
        output = llm_service.chat_completion(formatted_prompt, "배포 체크리스트 확인.")
        event["data"]["release"] = output
        return event
