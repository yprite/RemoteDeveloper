from typing import Dict, Any, Optional
import logging
from ..base import AgentStrategy
from ...core.llm import LLMService
from ...core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

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
        req = event["data"].get("requirement", "")
        formatted_prompt = self.prompt_template.format(requirement=req)
        
        output = llm_service.chat_completion(formatted_prompt, "계획을 수립해주세요.")
        event["data"]["plan"] = output
        return event
