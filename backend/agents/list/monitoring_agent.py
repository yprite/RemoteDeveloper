from typing import Dict, Any, Optional
import logging
from agents.base import AgentStrategy

logger = logging.getLogger("agents")


class MonitoringAgent(AgentStrategy):
    """
    Monitoring Agent - Currently SKIPPED.
    
    TODO: Implement monitoring setup (dashboards, alerts, metrics collection)
    """
    
    @property
    def name(self) -> str:
        return "MONITORING"
    
    @property
    def display_name(self) -> str:
        return "Monitoring 에이전트 (Skipped)"
    
    @property
    def prompt_template(self) -> str:
        return ""  # Not used
    
    @property
    def next_agent(self) -> Optional[str]:
        return None  # Final agent
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("meta", {}).get("event_id", "unknown")
        logger.info(f"[{self.name}] event={event_id} - Skipped (not implemented)")
        event["data"]["monitoring"] = "[Skipped] Monitoring Agent is currently disabled."
        return event

