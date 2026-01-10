"""
Pydantic Schema Models - Request/Response models for API endpoints.
"""
from pydantic import BaseModel
from typing import Optional, Union


# =============================================================================
# FILE & COMMAND SCHEMAS
# =============================================================================

class FileWriteRequest(BaseModel):
    """Request model for file write operations."""
    path: str
    content: str


class CommandRequest(BaseModel):
    """Request model for command execution."""
    command: str
    cwd: Optional[str] = None


# =============================================================================
# AGENT/PIPELINE SCHEMAS
# =============================================================================

class QueueRequest(BaseModel):
    """Request model for event ingestion."""
    task: Union[dict, str]
    context: Optional[Union[dict, str]] = {}


class ClarificationResponse(BaseModel):
    """Request model for user clarification response."""
    event_id: str
    response: str


# =============================================================================
# WORKFLOW SCHEMAS
# =============================================================================

class CreateWorkItemRequest(BaseModel):
    """Request model for creating a new WorkItem."""
    title: str
    meta: Optional[dict] = None
    workflow_name: str = "product_dev_v1"


class WorkflowEventRequest(BaseModel):
    """Request model for emitting workflow events."""
    name: str
    work_item_id: str
    payload: Optional[dict] = {}


class ApprovalRequest(BaseModel):
    """Request model for human approvals."""
    approval_type: str  # "UX", "ARCH", "RELEASE"
    approved: bool = True
    comment: Optional[str] = None
