"""
Workflow Router - Endpoints for WorkItem management and workflow events.
"""
from fastapi import APIRouter, HTTPException

from core.redis_client import get_redis
from core.logging_config import add_log
from core.schemas import CreateWorkItemRequest, WorkflowEventRequest, ApprovalRequest
from models import WorkflowEvent
from workflow import Orchestrator, WORKFLOW_REGISTRY

router = APIRouter(tags=["Workflow"])

# Get orchestrator instance (initialized in main.py)
_orchestrator = None


def get_orchestrator():
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        r = get_redis()
        if r:
            _orchestrator = Orchestrator(r)
    return _orchestrator


@router.post("/workitem")
def create_work_item(request: CreateWorkItemRequest):
    """
    Create a new WorkItem and start the workflow.
    
    This creates a WorkItem in the initial state (REQUIREMENTS) and
    triggers the on_enter actions (enqueue REQUIREMENT agent).
    """
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available (Redis not connected)")
    
    try:
        work_item = orchestrator.create_work_item(
            title=request.title,
            meta=request.meta,
            workflow_name=request.workflow_name
        )
        add_log("ORCHESTRATOR", f"Created WorkItem: {work_item.id} - {work_item.title}", "success")
        return {
            "status": "created",
            "work_item": work_item.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workitem/{work_item_id}")
def get_work_item(work_item_id: str):
    """Get WorkItem status and details."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    work_item = orchestrator.load_work_item(work_item_id)
    if not work_item:
        raise HTTPException(status_code=404, detail=f"WorkItem not found: {work_item_id}")
    
    return {"work_item": work_item.to_dict()}


@router.get("/workitems")
def list_work_items():
    """List all WorkItems."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    work_items = orchestrator.list_work_items()
    return {
        "count": len(work_items),
        "work_items": [wi.to_dict() for wi in work_items]
    }


@router.delete("/workitem/{work_item_id}")
def delete_work_item(work_item_id: str):
    """Delete a WorkItem."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    success = orchestrator.delete_work_item(work_item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"WorkItem not found: {work_item_id}")
    
    add_log("ORCHESTRATOR", f"Deleted WorkItem: {work_item_id}", "info")
    return {"status": "deleted", "work_item_id": work_item_id}


@router.post("/workflow/event")
def workflow_event(request: WorkflowEventRequest):
    """
    Emit a workflow event to trigger state transition.
    
    This is the main way agents report completion:
    - Agent finishes work
    - Agent publishes event (e.g., REQUIREMENTS_COMPLETED)
    - Orchestrator handles event and transitions WorkItem to next state
    """
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    event = WorkflowEvent(
        name=request.name,
        work_item_id=request.work_item_id,
        payload=request.payload or {},
        source="agent"
    )
    
    success, message = orchestrator.handle_event(event)
    
    if success:
        add_log("ORCHESTRATOR", f"Event processed: {request.name} for {request.work_item_id}", "success")
        
        work_item = orchestrator.load_work_item(request.work_item_id)
        return {
            "status": "processed",
            "message": message,
            "current_state": work_item.current_state if work_item else None
        }
    else:
        add_log("ORCHESTRATOR", f"Event failed: {message}", "failed")
        raise HTTPException(status_code=400, detail=message)


@router.post("/workitem/{work_item_id}/approve")
def approve_work_item(work_item_id: str, request: ApprovalRequest):
    """
    Submit human approval for a WorkItem.
    
    Approval types:
    - "UX": UX design approval (for DESIGN state)
    - "ARCH": Architecture approval (for DESIGN state)
    - "RELEASE": Release approval (for RELEASE state)
    """
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    success, message = orchestrator.submit_approval(
        work_item_id=work_item_id,
        approval_type=request.approval_type,
        approved=request.approved,
        comment=request.comment
    )
    
    if success:
        add_log("ORCHESTRATOR", f"Approval: {request.approval_type} for {work_item_id}", "success")
        work_item = orchestrator.load_work_item(work_item_id)
        return {
            "status": "approved" if request.approved else "rejected",
            "message": message,
            "current_state": work_item.current_state if work_item else None,
            "approval_flags": work_item.approval_flags if work_item else {}
        }
    else:
        add_log("ORCHESTRATOR", f"Approval failed: {message}", "failed")
        raise HTTPException(status_code=400, detail=message)


@router.get("/workflows")
def list_workflows():
    """List available workflow definitions."""
    return {
        "workflows": [
            {
                "name": wf.name,
                "initial_state": wf.initial_state,
                "states": list(wf.states.keys())
            }
            for wf in WORKFLOW_REGISTRY.values()
        ]
    }
