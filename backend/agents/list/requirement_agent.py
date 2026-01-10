from typing import Dict, Any, Optional
import json
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()

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
        prompt = event.get("task", {}).get("original_prompt", "")
        
        system_prompt = self.prompt_template.format(original_prompt=prompt)
        response_text = llm_service.chat_completion(system_prompt, "요구사항을 분석해주세요.", json_mode=True)
        
        try:
            result = json.loads(response_text)
        except:
            result = {"needs_clarification": False, "requirement_summary": response_text}

        if result.get("needs_clarification"):
            event["task"]["needs_clarification"] = True
            event["task"]["clarification_question"] = result.get("clarification_question")
            output = f"[요구사항 분석 중] 추가 정보 필요: {result.get('clarification_question')}"
        else:
            event["task"]["needs_clarification"] = False
            event["task"]["clarification_question"] = None
            output = f"[요구사항 정제 완료]\n{result.get('requirement_summary')}"
        
        event["data"]["requirement"] = output
        return event
