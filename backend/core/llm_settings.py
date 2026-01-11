"""
LLM Settings Module - Manages per-agent LLM adapter configuration.
"""
import json
import logging
from typing import Dict, Optional
from core.redis_client import get_redis

logger = logging.getLogger("llm_settings")

# Default LLM settings per agent
DEFAULT_LLM_SETTINGS: Dict[str, str] = {
    "REQUIREMENT": "openai",
    "PLAN": "openai",
    "UXUI": "openai",
    "ARCHITECT": "openai",
    "CODE": "claude_cli",          # Claude for code generation
    "REFACTORING": "cursor_cli",   # Cursor for refactoring
    "TESTQA": "openai",
    "DOC": "openai",
    "RELEASE": "openai",
    "MONITORING": "openai",
    "EVALUATION": "openai",
}

SETTINGS_KEY = "settings:llm"


def get_llm_settings() -> Dict[str, str]:
    """Get current LLM settings for all agents."""
    r = get_redis()
    if r:
        data = r.get(SETTINGS_KEY)
        if data:
            return json.loads(data)
    return DEFAULT_LLM_SETTINGS.copy()


def save_llm_settings(settings: Dict[str, str]) -> bool:
    """Save LLM settings for agents."""
    r = get_redis()
    if r:
        r.set(SETTINGS_KEY, json.dumps(settings))
        logger.info(f"LLM settings saved: {settings}")
        return True
    return False


def get_agent_adapter_name(agent_name: str) -> str:
    """Get the configured adapter name for an agent."""
    settings = get_llm_settings()
    return settings.get(agent_name.upper(), "openai")


def get_agent_adapter(agent_name: str):
    """Get the configured adapter instance for an agent."""
    from core.llm_adapter import get_adapter
    adapter_name = get_agent_adapter_name(agent_name)
    return get_adapter(adapter_name)


def get_available_adapters() -> list:
    """Get list of available adapter names."""
    from core.llm_adapter import ADAPTER_REGISTRY
    return list(ADAPTER_REGISTRY.keys())
