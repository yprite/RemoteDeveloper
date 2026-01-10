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
