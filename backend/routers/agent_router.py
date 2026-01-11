"""
Agent Router - Endpoints for agent processing and event ingestion.
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from agents import AGENT_REGISTRY, AGENT_ORDER
from core.redis_client import get_redis, push_event, pop_event
from core.logging_config import add_log, get_logs
from core.schemas import QueueRequest, ClarificationResponse

router = APIRouter(tags=["Agents"])


@router.get("/agent/logs")
def get_agent_logs():
    """Get all stored logs."""
    return {"logs": get_logs()}


@router.get("/agents")
def list_agents():
    """List all available agents with their info."""
    return {
        "agents": [
            {
                "name": agent.name,
                "display_name": agent.display_name,
                "queue": f"queue:{agent.name}",
                "next_agent": agent.next_agent
            }
            for agent in AGENT_REGISTRY.values()
        ],
        "order": AGENT_ORDER
    }


@router.post("/event/ingest")
def event_ingest(request: QueueRequest):
    """Ingress: Receives task and pushes to queue:REQUIREMENT (first agent)."""
    event_id = f"evt_{int(datetime.now().timestamp())}"
    
    if isinstance(request.task, str):
        task_data = {
            "title": f"Task-{event_id[-6:]}",
            "type": "CODE_ORCHESTRATION",
            "status": "PENDING",
            "current_stage": "REQUIREMENT",
            "original_prompt": request.task,
            "needs_clarification": False,
            "clarification_question": None,
            "git_context": None
        }
    else:
        task_data = request.task
        task_data["current_stage"] = "REQUIREMENT"
        task_data["needs_clarification"] = False
        task_data["clarification_question"] = None

    context_data = request.context
    if isinstance(context_data, str):
        try:
            context_data = json.loads(context_data)
        except:
            context_data = {"raw_parsing_error": str(context_data)}
    
    if context_data is None:
        context_data = {}

    event = {
        "meta": {
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "source": "api_ingress",
            "version": "1.0"
        },
        "context": context_data,
        "task": task_data,
        "data": {
            "requirement": None,
            "plan": None,
            "ux_ui": None,
            "architecture": None,
            "code": None,
            "refactoring": None,
            "test_results": None,
            "documentation": None,
            "release": None,
            "monitoring": None,
            "artifacts": []
        },
        "history": [{
            "stage": "INGRESS",
            "timestamp": datetime.now().isoformat(),
            "message": "Task ingested via API"
        }]
    }
    
    push_event("queue:REQUIREMENT", event)
    add_log("INGRESS", f"Ingested task: {event_id}", "success")
    return {"status": "queued", "event_id": event_id, "queue": "queue:REQUIREMENT"}


@router.post("/event/clarify")
def event_clarify(request: ClarificationResponse):
    """Handle user's clarification response for RequirementAgent."""
    r = get_redis()
    if not r:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    waiting_key = f"waiting:clarification:{request.event_id}"
    event_json = r.get(waiting_key)
    
    if not event_json:
        raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found in waiting")
    
    event = json.loads(event_json)
    
    original = event["task"].get("original_prompt", "")
    event["task"]["original_prompt"] = f"{original}\n\n[사용자 추가 정보]: {request.response}"
    event["task"]["needs_clarification"] = False
    event["task"]["clarification_question"] = None
    
    event["history"].append({
        "stage": "CLARIFICATION",
        "timestamp": datetime.now().isoformat(),
        "message": f"User provided clarification: {request.response[:50]}..."
    })
    
    r.delete(waiting_key)
    push_event("queue:REQUIREMENT", event)
    
    add_log("CLARIFICATION", f"Clarification received for {request.event_id}", "success")
    return {"status": "clarification_received", "event_id": request.event_id}


@router.post("/agent/{agent_name}/process")
def agent_process(agent_name: str):
    """Worker: Picks 1 item from queue:{agent_name}, processes it, pushes to next queue."""
    agent_key = agent_name.upper()
    
    if agent_key not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    agent = AGENT_REGISTRY[agent_key]
    queue_name = f"queue:{agent_key}"
    event = pop_event(queue_name)
    
    if not event:
        return {"status": "empty", "message": f"No events in {queue_name}"}

    event_id = event['meta']['event_id']
    add_log(agent_key, f"Processing event {event_id}", "running")
    
    # Process using agent strategy
    event = agent.process(event)
    
    # Special handling for RequirementAgent: check if clarification needed
    r = get_redis()
    if agent_key == "REQUIREMENT" and event["task"].get("needs_clarification"):
        waiting_key = f"waiting:clarification:{event_id}"
        if r:
            r.set(waiting_key, json.dumps(event))
        
        add_log(agent_key, f"Waiting for clarification: {event_id}", "pending")
        
        # Send Telegram Notification
        from core.telegram_bot import send_telegram_notification
        chat_id = event.get("context", {}).get("chat_id")
        if chat_id:
            logger.info(f"Sending Telegram notification to {chat_id}") # Add logger check
            send_telegram_notification(
                str(chat_id),
                f"❓ <b>추가 정보가 필요합니다</b>\n\n{event['task'].get('clarification_question')}\n\n"
                f"요청: {event['task'].get('original_prompt')[:50]}..."
            )
        
        return {
            "status": "needs_clarification",
            "event_id": event_id,
            "question": event["task"].get("clarification_question"),
            "agent": agent_key
        }
    
    # Update task status
    next_agent = agent.next_agent
    event["task"]["current_stage"] = next_agent if next_agent else "DONE"
    if not next_agent:
        event["task"]["status"] = "COMPLETED"
    
    # Update history
    output_data = event["data"].get(agent.get_data_key(), "")
    event["history"].append({
        "stage": agent_key,
        "timestamp": datetime.now().isoformat(),
        "message": f"Processed by {agent.display_name}",
        "output_summary": str(output_data)[:100] + "..."
    })
    
    # Push to next queue or finish
    if next_agent:
        next_queue = f"queue:{next_agent}"
        push_event(next_queue, event)
        msg = f"Completed. Next -> {next_agent}"
    else:
        msg = "Pipeline Completed."
        add_log("SYSTEM", f"Workflow Finished for {event_id}", "success")

    add_log(agent_key, msg, "success")
    
    return {
        "status": "processed",
        "agent": agent_key,
        "display_name": agent.display_name,
        "output": event["data"].get(agent.get_data_key(), ""),
        "next_queue": f"queue:{next_agent}" if next_agent else None
    }


@router.get("/queues")
def get_queues():
    """Get content of all active queues."""
    queues = {}
    target_queues = [f"queue:{name}" for name in AGENT_ORDER]
    
    r = get_redis()
    if r:
        for q in target_queues:
            items = r.lrange(q, 0, -1)
            parsed_items = []
            for item in items:
                try:
                    parsed_items.append(json.loads(item))
                except:
                    parsed_items.append({"raw": item})
            queues[q] = {"count": len(parsed_items), "items": parsed_items}
        
        # Also check waiting clarifications
        waiting_keys = r.keys("waiting:clarification:*")
        waiting = {}
        for key in waiting_keys:
            event_json = r.get(key)
            if event_json:
                waiting[key] = json.loads(event_json)
        queues["waiting:clarification"] = {"count": len(waiting), "items": waiting}
    else:
        return {"error": "Redis not connected"}
        
    return {"queues": queues}


@router.post("/pipeline/run-all")
def run_pipeline():
    """Process one event through the entire pipeline (for testing)."""
    results = []
    
    for agent_name in AGENT_ORDER:
        result = agent_process(agent_name)
        results.append({"agent": agent_name, "result": result})
        
        # Stop if needs clarification or empty
        if result.get("status") in ["needs_clarification", "empty"]:
            break
    
    return {"pipeline_results": results}


# =============================================================================
# PENDING ACTIONS API (Human-in-the-loop)
# =============================================================================

from pydantic import BaseModel

class PendingResponseRequest(BaseModel):
    """Request model for pending item response."""
    response: str


@router.get("/pending")
def get_pending_items():
    """
    Get all pending items requiring human action.
    
    Returns:
        - Clarification requests (from Requirements Agent)
        - Approval requests (from DESIGN state: UX/ARCH approvals)
    """
    r = get_redis()
    if not r:
        return {"error": "Redis not connected", "pending_items": []}
    
    pending_items = []
    
    # 1. Get clarification requests
    clarification_keys = r.keys("waiting:clarification:*")
    for key in clarification_keys:
        event_json = r.get(key)
        if event_json:
            event = json.loads(event_json)
            event_id = key.replace("waiting:clarification:", "")
            pending_items.append({
                "id": event_id,
                "type": "clarification",
                "question": event.get("task", {}).get("clarification_question", "추가 정보가 필요합니다"),
                "original_prompt": event.get("task", {}).get("original_prompt", ""),
                "created_at": event.get("meta", {}).get("timestamp", ""),
                "context": event.get("context", {})
            })
    
    # 1.5 Get approval requests from Agent pipeline (NEW)
    approval_keys = r.keys("waiting:approval:*")
    for key in approval_keys:
        event_json = r.get(key)
        if event_json:
            event = json.loads(event_json)
            event_id = key.replace("waiting:approval:", "")
            pending_items.append({
                "id": event_id,
                "type": "approval",
                "title": event.get("task", {}).get("original_prompt", "")[:50],
                "current_state": event.get("task", {}).get("current_stage", ""),
                "pending_approvals": [event.get("task", {}).get("current_stage", "UNKNOWN")],
                "message": event.get("task", {}).get("approval_message", "승인이 필요합니다"),
                "created_at": event.get("meta", {}).get("timestamp", ""),
                "context": event.get("context", {})
            })
    
    # 1.6 Get debug mode pending items (NEW)
    debug_keys = r.keys("waiting:debug:*")
    for key in debug_keys:
        event_json = r.get(key)
        if event_json:
            event = json.loads(event_json)
            # key format: waiting:debug:{event_id}:{agent_name}
            parts = key.split(":")
            event_id = parts[2] if len(parts) > 2 else "unknown"
            agent_name = parts[3] if len(parts) > 3 else "UNKNOWN"
            pending_items.append({
                "id": f"{event_id}:{agent_name}",
                "type": "debug",
                "agent": agent_name,
                "title": f"[{agent_name}] {event.get('task', {}).get('original_prompt', '')[:40]}...",
                "current_state": agent_name,
                "message": f"디버깅 모드: {agent_name} 에이전트 실행 승인 필요",
                "created_at": event.get("meta", {}).get("timestamp", ""),
                "context": event.get("context", {})
            })
    
    # 2. Get pending approvals from WorkItems in DESIGN state
    # (These are stored by the workflow orchestrator)
    from workflow.orchestrator import Orchestrator
    orchestrator = Orchestrator(r)
    work_items = orchestrator.list_work_items()
    
    for wi in work_items:
        # Check if in DESIGN state with pending approvals
        if wi.current_state == "DESIGN":
            pending_approvals = []
            if not wi.approval_flags.get("UX_APPROVED"):
                pending_approvals.append("UX")
            if not wi.approval_flags.get("ARCH_APPROVED"):
                pending_approvals.append("ARCH")
            
            if pending_approvals:
                pending_items.append({
                    "id": wi.id,
                    "type": "approval",
                    "title": wi.title,
                    "current_state": wi.current_state,
                    "pending_approvals": pending_approvals,
                    "approval_flags": wi.approval_flags,
                    "created_at": wi.created_at.isoformat() if hasattr(wi.created_at, 'isoformat') else str(wi.created_at),
                    "meta": wi.meta
                })
        
        # Check if in RELEASE state needing approval
        elif wi.current_state == "RELEASE":
            pending_items.append({
                "id": wi.id,
                "type": "approval",
                "title": wi.title,
                "current_state": wi.current_state,
                "pending_approvals": ["RELEASE"],
                "created_at": wi.created_at.isoformat() if hasattr(wi.created_at, 'isoformat') else str(wi.created_at),
                "meta": wi.meta
            })
    
    # Sort by created_at (newest first)
    pending_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "count": len(pending_items),
        "pending_items": pending_items
    }


@router.post("/pending/{item_id}/respond")
def respond_to_pending(item_id: str, request: PendingResponseRequest):
    """
    Submit a response to a pending clarification request.
    
    This is equivalent to /event/clarify but with a simpler interface.
    """
    r = get_redis()
    if not r:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    waiting_key = f"waiting:clarification:{item_id}"
    event_json = r.get(waiting_key)
    
    if not event_json:
        raise HTTPException(status_code=404, detail=f"Pending item not found: {item_id}")
    
    event = json.loads(event_json)
    
    # Append response to original prompt
    original = event["task"].get("original_prompt", "")
    event["task"]["original_prompt"] = f"{original}\n\n[사용자 추가 정보]: {request.response}"
    event["task"]["needs_clarification"] = False
    event["task"]["clarification_question"] = None
    
    # Add to history
    event["history"].append({
        "stage": "CLARIFICATION_RESPONSE",
        "timestamp": datetime.now().isoformat(),
        "message": f"User responded: {request.response[:100]}..."
    })
    
    # Remove from waiting and push back to requirement queue
    r.delete(waiting_key)
    push_event("queue:REQUIREMENT", event)
    
    add_log("PENDING", f"Clarification response received for {item_id}", "success")
    
    return {
        "status": "responded",
        "item_id": item_id,
        "message": "Response submitted. Item moved back to processing queue."
    }

