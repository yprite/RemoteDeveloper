"""
LLM Service Module - High-level interface for LLM operations.
Uses the adapter pattern to support multiple LLM backends.
"""
import os
import json
import re
import logging
from typing import Optional

logger = logging.getLogger("llm")


class LLMService:
    """Main LLM service that uses adapters based on agent configuration."""
    
    def __init__(self, agent_name: Optional[str] = None):
        """
        Initialize LLM service.
        
        Args:
            agent_name: If provided, uses the adapter configured for this agent.
                       Otherwise uses OpenAI as default.
        """
        self.agent_name = agent_name
        self._adapter = None
    
    def _get_adapter(self):
        """Get the appropriate adapter based on agent configuration."""
        if self._adapter is None:
            if self.agent_name:
                from core.llm_settings import get_agent_adapter
                self._adapter = get_agent_adapter(self.agent_name)
            else:
                from core.llm_adapter import OpenAIAdapter
                self._adapter = OpenAIAdapter()
        return self._adapter
    
    def chat_completion(self, 
                        system_prompt: str, 
                        user_prompt: str, 
                        model: Optional[str] = None,
                        json_mode: bool = False) -> str:
        """
        Generate a chat completion using the configured adapter.
        
        Args:
            system_prompt: System/instruction prompt
            user_prompt: User query
            model: (Ignored - for backward compatibility)
            json_mode: Whether to request JSON output
            
        Returns:
            Generated text response
        """
        adapter = self._get_adapter()
        return adapter.generate(system_prompt, user_prompt, json_mode)
