"""WorkItem Model - represents a single work unit in the workflow."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import json


@dataclass
class WorkItem:
    """
    WorkItem represents a single feature/story/task unit that flows through the workflow.
    
    Attributes:
        id: Unique identifier (UUID)
        title: Human-readable title for the work item
        current_state: Current state in the workflow (e.g., "REQUIREMENTS", "CODING")
        workflow_name: Name of the workflow definition to use
        meta: Additional metadata (priority, tags, domain, etc.)
        approval_flags: For states requiring multiple approvals (e.g., DESIGN needs UX + ARCH)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        history: List of state transition history entries
    """
    id: str
    title: str
    current_state: str
    workflow_name: str = "product_dev_v1"
    meta: dict = field(default_factory=dict)
    approval_flags: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    history: list = field(default_factory=list)
    
    @classmethod
    def create(cls, title: str, meta: Optional[dict] = None, 
               workflow_name: str = "product_dev_v1") -> "WorkItem":
        """Factory method to create a new WorkItem with generated ID."""
        work_item_id = f"wi_{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        return cls(
            id=work_item_id,
            title=title,
            current_state="REQUIREMENTS",  # Initial state
            workflow_name=workflow_name,
            meta=meta or {},
            approval_flags={},
            created_at=now,
            updated_at=now,
            history=[{
                "state": "CREATED",
                "timestamp": now.isoformat(),
                "message": "WorkItem created"
            }]
        )
    
    def add_history(self, state: str, message: str):
        """Add a history entry."""
        self.history.append({
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "message": message
        })
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "current_state": self.current_state,
            "workflow_name": self.workflow_name,
            "meta": self.meta,
            "approval_flags": self.approval_flags,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "history": self.history
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorkItem":
        """Create WorkItem from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return cls(
            id=data["id"],
            title=data["title"],
            current_state=data["current_state"],
            workflow_name=data.get("workflow_name", "product_dev_v1"),
            meta=data.get("meta", {}),
            approval_flags=data.get("approval_flags", {}),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            history=data.get("history", [])
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "WorkItem":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
