"""
Agent Base Module - Abstract base class for all agents.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AgentStrategy(ABC):
    """Abstract base class for all agents using Strategy Pattern."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name (used for queue name)."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human readable agent name."""
        pass
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """System prompt template for this agent."""
        pass
    
    @property
    @abstractmethod
    def next_agent(self) -> Optional[str]:
        """Next agent in the pipeline, None if last."""
        pass
    
    @abstractmethod
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process event and return updated event with output."""
        pass
    
    def get_data_key(self) -> str:
        """Key to store output in event['data']."""
        return self.name.lower()
    
    def get_llm_service(self):
        """Get LLMService configured for this agent's adapter."""
        from core.llm import LLMService
        return LLMService(agent_name=self.name)
