from typing import Dict, Any, Optional
import logging
from ..base import AgentStrategy
from ...core.llm import LLMService
from ...core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

class MonitoringAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "MONITORING"
    
    @property
    def display_name(self) -> str:
        return "Monitoring 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return None
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        output = llm_service.chat_completion(self.prompt_template, "모니터링 설정을 제안해주세요.")
        event["data"]["monitoring"] = output
        return event
