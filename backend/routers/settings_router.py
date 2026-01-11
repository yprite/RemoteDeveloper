"""
Settings Router - API endpoints for system settings.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from core.llm_settings import (
    get_llm_settings, 
    save_llm_settings, 
    get_available_adapters,
    DEFAULT_LLM_SETTINGS
)
from core.database import (
    get_repositories,
    add_repository,
    remove_repository
)
from core.rag_scheduler import trigger_indexing
from core.rag_service import get_rag_service

router = APIRouter(tags=["Settings"])


# =============================================================================
# LLM SETTINGS
# =============================================================================

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


# =============================================================================
# REPOSITORY SETTINGS
# =============================================================================

class AddRepoRequest(BaseModel):
    """Request model for adding a repository."""
    url: str
    name: Optional[str] = None


@router.get("/settings/repos")
def list_repositories():
    """Get all tracked repositories."""
    try:
        repos = get_repositories(active_only=True)
        return {"repositories": repos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/repos")
def add_repo(request: AddRepoRequest):
    """Add a repository to track and index."""
    try:
        repo_id = add_repository(request.url, request.name)
        # Trigger indexing in background
        trigger_indexing()
        return {
            "status": "added",
            "id": repo_id,
            "message": "Repository added. Indexing will start shortly."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/settings/repos/{repo_id}")
def delete_repo(repo_id: int):
    """Remove a repository from tracking."""
    try:
        remove_repository(repo_id)
        return {"status": "removed", "id": repo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/repos/reindex")
def trigger_reindex():
    """Manually trigger re-indexing of all repositories."""
    trigger_indexing()
    return {"status": "indexing_started"}


# =============================================================================
# RAG STATS
# =============================================================================

@router.get("/settings/rag/stats")
def get_rag_stats():
    """Get RAG database statistics."""
    try:
        rag = get_rag_service()
        return rag.get_stats()
    except Exception as e:
        return {"error": str(e), "total_documents": 0}
