"""
AI Development Team Server - Main Application Entry Point.

This is the central FastAPI application that orchestrates:
- 11 AI agents for product development workflow
- Event-driven queue processing via Redis
- Background worker for automatic queue processing
"""
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize core components
from core.logging_config import setup_logging
from core.redis_client import init_redis

# Import routers
from routers import agent_router, workflow_router, file_router, system_router, metrics_router, settings_router, tasks_router
from agents import AGENT_REGISTRY

# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(title="AI Development Team Server")

# Setup logging
setup_logging()

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# INITIALIZE SERVICES
# =============================================================================

# Initialize SQLite database
from core.database import init_database
init_database()

# Initialize Redis connection
init_redis()

# Start background worker
from core.worker import start_worker
start_worker()

# Start RAG scheduler (background indexing)
from core.rag_scheduler import start_rag_scheduler
start_rag_scheduler()

# Start PR wait service (polling for merge + review handling)
from core.pr_wait_service import get_pr_wait_service, PendingPR
from core.pr_review_service import get_pr_review_service, ReviewFeedback
import logging

_pr_logger = logging.getLogger("pr_feedback")


def _handle_pr_merged(pending: PendingPR):
    """Handle PR merge - trigger next agent."""
    from core.redis_client import get_redis
    import json
    redis = get_redis()
    if redis and pending.next_agent:
        queue_name = f"queue:{pending.next_agent}"
        event_data = pending.event_data
        event_data["status"] = "PR_MERGED"
        redis.rpush(queue_name, json.dumps(event_data))
        _pr_logger.info(f"PR merged - queued event to {pending.next_agent}")


def _handle_changes_requested(pending: PendingPR, feedback: ReviewFeedback):
    """Handle changes requested - trigger rework."""
    from core.redis_client import get_redis
    from core.pr_review_service import get_pr_review_service
    import json
    
    redis = get_redis()
    if redis:
        # Create rework event
        review_service = get_pr_review_service()
        rework_event = review_service.create_rework_event(
            original_event=pending.event_data,
            feedback=feedback,
            agent_name=pending.agent_name
        )
        
        # Queue to same agent for rework
        queue_name = f"queue:{pending.agent_name}"
        redis.rpush(queue_name, json.dumps(rework_event))
        _pr_logger.info(f"Changes requested - queued rework to {pending.agent_name}")


# Initialize and start PR wait service
_pr_wait = get_pr_wait_service()
_pr_wait.set_merged_callback(_handle_pr_merged)
_pr_wait.set_changes_requested_callback(_handle_changes_requested)
_pr_wait.start_polling()

# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

app.include_router(agent_router)
app.include_router(workflow_router)
app.include_router(file_router)
app.include_router(system_router)
app.include_router(metrics_router)
app.include_router(settings_router)
app.include_router(tasks_router)

# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "status": "active",
        "service": "ai-dev-team-server",
        "agents": len(AGENT_REGISTRY)
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="error", access_log=False)
