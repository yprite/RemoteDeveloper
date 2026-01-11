"""
Tasks Router - API endpoints for task history.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from core.database import get_tasks, get_task_detail

router = APIRouter(tags=["Tasks"])


@router.get("/tasks")
def list_tasks(limit: int = 50):
    """Get recent tasks."""
    tasks = get_tasks(limit=limit)
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get task detail with event sequence."""
    task = get_task_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
