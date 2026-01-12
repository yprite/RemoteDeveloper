from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy

logger = logging.getLogger("agents")


class ReleaseAgent(AgentStrategy):
    """
    Release Agent - Currently SKIPPED.
    
    TODO: Implement release automation (CI/CD triggers, version bumps, etc.)
    """
    
    @property
    def name(self) -> str:
        return "RELEASE"
    
    @property
    def display_name(self) -> str:
        return "Release 에이전트 (Skipped)"
    
    @property
    def prompt_template(self) -> str:
        return ""  # Not used
    
    @property
    def next_agent(self) -> Optional[str]:
        return "MONITORING"
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        logger.info(f"[{self.name}] event={event_id} - Skipped (not implemented)")
        event["data"]["release"] = "[Skipped] Release Agent is currently disabled."
        return event

