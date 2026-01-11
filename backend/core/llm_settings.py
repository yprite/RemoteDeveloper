"""
LLM Settings Module - Manages per-agent LLM adapter configuration using SQLite.
"""
import logging
from typing import Dict

logger = logging.getLogger("llm_settings")

# Default LLM settings per agent
DEFAULT_LLM_SETTINGS: Dict[str, str] = {
    "REQUIREMENT": "openai",
    "PLAN": "openai",
    "UXUI": "openai",
    "ARCHITECT": "openai",
    "CODE": "claude_cli",
    "REFACTORING": "cursor_cli",
    "TESTQA": "openai",
    "DOC": "openai",
    "RELEASE": "openai",
    "MONITORING": "openai",
    "EVALUATION": "openai",
}


def get_llm_settings() -> Dict[str, str]:
    """Get current LLM settings for all agents from SQLite."""
    try:
        from core.database import get_llm_settings as db_get_llm_settings
        settings = db_get_llm_settings()
        if settings:
            return settings
    except Exception as e:
        logger.warning(f"Failed to get LLM settings from DB: {e}")
    return DEFAULT_LLM_SETTINGS.copy()


def save_llm_settings(settings: Dict[str, str]) -> bool:
    """Save LLM settings for agents to SQLite."""
    try:
        from core.database import set_llm_settings_bulk
        set_llm_settings_bulk(settings)
        logger.info(f"LLM settings saved")
        return True
    except Exception as e:
        logger.error(f"Failed to save LLM settings: {e}")
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
