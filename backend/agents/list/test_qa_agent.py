from typing import Dict, Any, Optional
import logging
from ..base import AgentStrategy
from ...core.llm import LLMService
from ...core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

class TestQaAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "TESTQA"
    
    @property
    def display_name(self) -> str:
        return "TEST/QA 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return "DOC"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        code_summary = event["data"].get("code", "")
        formatted_prompt = self.prompt_template.format(code=code_summary)
        
        output = llm_service.chat_completion(formatted_prompt, "테스트 시나리오를 작성해주세요.")
        event["data"]["test_results"] = output
        return event
