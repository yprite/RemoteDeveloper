"""WorkflowEvent Model - represents an event that triggers state transitions."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class WorkflowEvent:
    """
    WorkflowEvent represents a domain event that triggers state transitions.
    
    These events are published by agents after completing their work,
    or by humans (via UI) for approval actions.
    
    Attributes:
        name: Event name (e.g., "REQUIREMENTS_COMPLETED", "QA_PASSED", "UX_APPROVED")
        work_item_id: ID of the WorkItem this event applies to
        payload: Additional data (test coverage, report URL, etc.)
        created_at: Event creation timestamp
        source: Origin of the event ("agent", "human", "system")
    """
    name: str
    work_item_id: str
    payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "system"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "work_item_id": self.work_item_id,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowEvent":
        """Create WorkflowEvent from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            name=data["name"],
            work_item_id=data["work_item_id"],
            payload=data.get("payload", {}),
            created_at=created_at or datetime.now(),
            source=data.get("source", "system")
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowEvent":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Standard event names for reference
class EventNames:
    """Standard workflow event names."""
    # System Events
    WORK_ITEM_CREATED = "WORK_ITEM_CREATED"
    
    # Requirements Agent
    REQUIREMENTS_COMPLETED = "REQUIREMENTS_COMPLETED"
    REQUIREMENTS_NEEDS_MORE_INFO = "REQUIREMENTS_NEEDS_MORE_INFO"
    
    # Plan Agent
    PLAN_COMPLETED = "PLAN_COMPLETED"
    PLAN_SCOPE_CHANGED = "PLAN_SCOPE_CHANGED"
    
    # Design (UX + Architecture)
    UX_APPROVED = "UX_APPROVED"
    ARCH_APPROVED = "ARCH_APPROVED"
    UX_ARCH_DONE = "UX_ARCH_DONE"  # Auto-generated when both approved
    
    # Code Agent
    CODE_READY_FOR_QA = "CODE_READY_FOR_QA"
    CODE_NEEDS_REFACTOR = "CODE_NEEDS_REFACTOR"
    
    # Refactor Agent
    REFACTOR_DONE = "REFACTOR_DONE"
    
    # QA Agent
    QA_PASSED = "QA_PASSED"
    QA_FAILED = "QA_FAILED"
    QA_SCOPE_CHANGE = "QA_SCOPE_CHANGE"
    
    # Doc Agent
    DOC_DONE = "DOC_DONE"
    
    # Release Agent
    RELEASED = "RELEASED"
    
    # Monitoring Agent
    INCIDENT_HOTFIX = "INCIDENT_HOTFIX"
    NEW_FEATURE_IDEA = "NEW_FEATURE_IDEA"
