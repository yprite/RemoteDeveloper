from typing import Dict, Any, Optional
import logging
from ..base import AgentStrategy
from ...core.llm import LLMService
from ...core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

class DocAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "DOC"
    
    @property
    def display_name(self) -> str:
        return "DOC 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "RELEASE"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        code = event["data"].get("code", "")
        test = event["data"].get("test_results", "")
        
        formatted_prompt = self.prompt_template.format(code=code, test_results=test)
        
        output = llm_service.chat_completion(formatted_prompt, "문서를 작성해주세요.")
        event["data"]["documentation"] = output
        return event
