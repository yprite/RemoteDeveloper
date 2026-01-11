"""
Pydantic Schema Models - Request/Response models for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any
from datetime import datetime


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
# AGENT EVENT SCHEMAS
# =============================================================================

class EventMeta(BaseModel):
    """Metadata for an agent event."""
    event_id: str
    timestamp: str
    source: str = "api_ingress"
    version: str = "1.0"


class TaskData(BaseModel):
    """Task information passed through the pipeline."""
    title: str = ""
    type: str = "CODE_ORCHESTRATION"
    status: str = "PENDING"
    current_stage: str = "REQUIREMENT"
    original_prompt: str = ""
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    git_context: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow extra fields


class AgentOutputs(BaseModel):
    """Output data from each agent in the pipeline."""
    requirement: Optional[str] = None
    plan: Optional[str] = None
    ux_ui: Optional[str] = None
    architecture: Optional[str] = None
    code: Optional[str] = None
    refactoring: Optional[str] = None
    test_results: Optional[str] = None
    documentation: Optional[str] = None
    release: Optional[str] = None
    monitoring: Optional[str] = None
    evaluation: Optional[str] = None
    achievement_score: Optional[int] = None
    artifacts: List[Any] = Field(default_factory=list)
    
    class Config:
        extra = "allow"  # Allow extra fields for flexibility


class HistoryEntry(BaseModel):
    """A single entry in the event history."""
    stage: str
    timestamp: str
    message: str
    output_summary: Optional[str] = None


class AgentEvent(BaseModel):
    """
    Complete event schema for agent pipeline.
    This is the contract between all agents.
    """
    meta: EventMeta
    context: Dict[str, Any] = Field(default_factory=dict)
    task: TaskData
    data: AgentOutputs = Field(default_factory=AgentOutputs)
    history: List[HistoryEntry] = Field(default_factory=list)
    
    class Config:
        extra = "allow"  # Allow extra fields
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentEvent":
        """Create AgentEvent from dictionary with validation."""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()


# =============================================================================
# AGENT/PIPELINE SCHEMAS (Original)
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
