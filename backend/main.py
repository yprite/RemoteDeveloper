import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime
import logging
import sys

app = FastAPI(title="AI Code Agent Server")

# Log storage
logs = []

# --- System Logging Interceptor ---
class InMemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            # Map python levels to our status types
            status = "info"
            if level in ["warning"]: status = "pending" # distinct color?
            if level in ["error", "critical"]: status = "failed"
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "agent": "SYSTEM",  # or record.name
                "message": msg,
                "status": status
            }
            logs.append(entry)
            # Keep only last 200 logs
            if len(logs) > 200:
                logs.pop(0)
        except Exception:
            self.handleError(record)

# Setup logging
log_handler = InMemoryLogHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)

# Attach to root logger and uvicorn
logging.getLogger().addHandler(log_handler)
logging.getLogger("uvicorn").addHandler(log_handler)
logging.getLogger("uvicorn.access").addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FileWriteRequest(BaseModel):
    path: str
    content: str

class CommandRequest(BaseModel):
    command: str
    cwd: Optional[str] = None

@app.get("/")
def health_check():
    return {"status": "active", "service": "code-agent-server"}

@app.get("/files/list")
def list_files(path: str = "."):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    files = []
    for root, dirs, filenames in os.walk(path):
        # Limit depth? For now just flat list relative paths could be heavy, 
        # let's just do top level or implement specific logic if needed.
        # Actually, let's just do os.listdir for now to keep it simple and safe.
        return {"files": os.listdir(path)}

@app.post("/files/read")
def read_file(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(path, "r") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/write")
def write_file(request: FileWriteRequest):
    try:
        # Ensure directory exists
        directory = os.path.dirname(request.path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(request.path, "w") as f:
            f.write(request.content)
        return {"status": "success", "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/command/run")
def run_command(request: CommandRequest):
    try:
        current_cwd = request.cwd or os.getcwd()
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=current_cwd,
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Simple Linear Agent Endpoints ---

# --- Event-Driven Queue Logic ---

import redis
import json

# Redis Connection
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print("[REDIS] Connected successfully")
except Exception as e:
    print(f"[REDIS] Connection failed: {e}")
    r = None

def add_log(agent: str, message: str, status: str = "info"):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "message": message,
        "status": status
    }
    logs.append(entry)
    # Keep only last 100 logs
    if len(logs) > 100:
        logs.pop(0)

@app.get("/agent/logs")
def get_agent_logs():
    return {"logs": logs}

class QueueRequest(BaseModel):
    task: Union[dict, str] # Support both for flexibility
    context: Optional[Union[dict, str]] = {}

class ProcessRequest(BaseModel):
    pass 

def push_event(queue_name: str, event: dict):
    if r:
        r.rpush(queue_name, json.dumps(event))
        add_log("SYSTEM", f"Pushed event to {queue_name}", "info")
    else:
        add_log("SYSTEM", "Redis not available", "failed")

def pop_event(queue_name: str) -> Optional[dict]:
    if r:
        # Non-blocking pop
        item = r.lpop(queue_name)
        if item:
            return json.loads(item)
    return None

@app.post("/event/ingest")
def event_ingest(request: QueueRequest):
    """
    Ingress: Receives task from n8n (Telegram) and pushes to queue:PLAN.
    """
    event_id = f"evt_{int(datetime.now().timestamp())}"
    
    # Handle task input
    if isinstance(request.task, str):
        task_data = {
            "title": f"Task-{event_id[-6:]}",
            "type": "CODE_ORCHESTRATION",
            "status": "PENDING",
            "current_stage": "PLAN",
            "original_prompt": request.task,
            "git_context": None
        }
    else:
        task_data = request.task

    # Handle context input (n8n might send string "[object Object]" or JSON string)
    context_data = request.context
    if isinstance(context_data, str):
        try:
            context_data = json.loads(context_data)
        except:
            # Fallback for malformed strings
            context_data = {"raw_parsing_error": str(context_data)}
    
    if context_data is None:
        context_data = {}

    # Construct event based on new schema
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
            "plan": None,
            "code": None,
            "test_results": None,
            "artifacts": []
        },
        "history": [{
            "stage": "INGRESS",
            "timestamp": datetime.now().isoformat(),
            "message": "Task ingested via API"
        }]
    }
    
    push_event("queue:PLAN", event)
    add_log("INGRESS", f"Ingested task: {event_id}", "success")
    return {"status": "queued", "event_id": event_id, "queue": "queue:PLAN"}

@app.post("/agent/{agent_name}/process")
def agent_process(agent_name: str):
    """
    Worker: Picks 1 item from queue:{agent_name}, processes it, pushes to next queue.
    """
    queue_name = f"queue:{agent_name.upper()}"
    event = pop_event(queue_name)
    
    if not event:
        return {"status": "empty", "message": f"No events in {queue_name}"}

    event_id = event['meta']['event_id']
    add_log(agent_name.upper(), f"Processing event {event_id}", "running")
    
    # --- PROCESSSING LOGIC (Mock LLM) ---
    # Safely get prompt from nested structure
    task_prompt = event.get("task", {}).get("original_prompt", "No prompt")
    
    output = ""
    next_agent = None
    
    if agent_name.upper() == "PLAN":
        output = f"Plan for '{task_prompt}':\n1. Step A\n2. Step B"
        # Store in data.plan
        event["data"]["plan"] = output
        next_agent = "IMPLEMENTATION"
        
    elif agent_name.upper() == "IMPLEMENTATION":
        output = "def solution():\n    print('Solved')"
        # Store in data.code
        event["data"]["code"] = output
        next_agent = "TEST"
        
    elif agent_name.upper() == "TEST":
        output = "Tests passed successfully."
        # Store in data.test_results
        event["data"]["test_results"] = output
        next_agent = "DONE" # End of line
    
    # Update Status
    if "task" in event:
        event["task"]["current_stage"] = next_agent if next_agent else "DONE"
        if next_agent == "DONE":
            event["task"]["status"] = "COMPLETED"

    # Update History
    event["history"].append({
        "stage": agent_name.upper(),
        "timestamp": datetime.now().isoformat(),
        "message": f"Processed by {agent_name}",
        "output_summary": output[:50] + "..."
    })
    
    # Push to Next
    if next_agent and next_agent != "DONE":
        next_queue = f"queue:{next_agent}"
        push_event(next_queue, event)
        msg = f"Completed. Next -> {next_agent}"
    else:
        msg = "Pipeline Completed."
        add_log("SYSTEM", f"Workflow Finished for {event_id}", "success")

    add_log(agent_name.upper(), msg, "success")
    
    return {
        "status": "processed", 
        "agent": agent_name, 
        "output": output, 
        "next_queue": f"queue:{next_agent}" if next_agent else "None"
    }

@app.get("/queues")
def get_queues():
    """
    Get content of all active queues
    """
    queues = {}
    target_queues = ["queue:PLAN", "queue:IMPLEMENTATION", "queue:TEST"]
    
    if r:
        for q in target_queues:
            # Get all items
            items = r.lrange(q, 0, -1)
            # Parse JSON
            parsed_items = []
            for item in items:
                try:
                    parsed_items.append(json.loads(item))
                except:
                    parsed_items.append({"raw": item}) # Fallback
            queues[q] = parsed_items
    else:
        return {"error": "Redis not connected"}
        
    return {"queues": queues}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
