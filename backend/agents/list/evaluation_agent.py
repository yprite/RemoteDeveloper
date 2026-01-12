from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy

logger = logging.getLogger("agents")


class EvaluationAgent(AgentStrategy):
    """
    Evaluation Agent - Currently SKIPPED.
    
    TODO: Implement pipeline evaluation and metrics collection
    """
    
    @property
    def name(self) -> str:
        return "EVALUATION"
    
    @property
    def display_name(self) -> str:
        return "작업 평가 에이전트 (Skipped)"
    
    @property
    def prompt_template(self) -> str:
        return ""  # Not used
    
    @property
    def next_agent(self) -> Optional[str]:
        return None  # Last agent in pipeline
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        logger.info(f"[{self.name}] event={event_id} - Skipped (not implemented)")
        event["data"]["evaluation"] = "[Skipped] Evaluation Agent is currently disabled."
        event["data"]["achievement_score"] = 0
        return event

