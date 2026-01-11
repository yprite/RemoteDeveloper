"""
Settings Router - API endpoints for system settings.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from core.llm_settings import (
    get_llm_settings, 
    save_llm_settings, 
    get_available_adapters,
    DEFAULT_LLM_SETTINGS
)

router = APIRouter(tags=["Settings"])


class LLMSettingsRequest(BaseModel):
    """Request model for updating LLM settings."""
    settings: Dict[str, str]


@router.get("/settings/llm")
def get_settings():
    """Get current LLM settings for all agents."""
    return {
        "settings": get_llm_settings(),
        "defaults": DEFAULT_LLM_SETTINGS
    }


@router.post("/settings/llm")
def update_settings(request: LLMSettingsRequest):
    """Update LLM settings for agents."""
    success = save_llm_settings(request.settings)
    return {
        "status": "saved" if success else "failed",
        "settings": get_llm_settings()
    }


@router.get("/settings/llm/adapters")
def get_adapters():
    """Get list of available LLM adapters."""
    adapters = get_available_adapters()
    return {
        "adapters": [
            {"name": "openai", "label": "OpenAI GPT-4o", "description": "OpenAI API"},
            {"name": "claude_cli", "label": "Claude CLI", "description": "Anthropic Claude via CLI"},
            {"name": "cursor_cli", "label": "Cursor CLI", "description": "Cursor AI via CLI"},
        ]
    }


@router.post("/settings/llm/reset")
def reset_settings():
    """Reset LLM settings to defaults."""
    save_llm_settings(DEFAULT_LLM_SETTINGS)
    return {
        "status": "reset",
        "settings": DEFAULT_LLM_SETTINGS
    }
