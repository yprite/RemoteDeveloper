"""
RAG Scheduler Module - Background scheduler for repository indexing.
Runs periodic indexing of registered repositories.
"""
import os
import threading
import time
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger("rag_scheduler")

# Configuration
INDEX_INTERVAL_MINUTES = 10
REPOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "repos")

# Scheduler state
_scheduler_thread: Optional[threading.Thread] = None
_scheduler_running = False


def _clone_or_pull_repo(url: str, local_path: str) -> bool:
    """Clone a repository or pull if already exists."""
    import subprocess
    
    try:
        if os.path.exists(os.path.join(local_path, ".git")):
            # Pull latest
            result = subprocess.run(
                ["git", "pull", "--quiet"],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.returncode == 0
        else:
            # Clone
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            result = subprocess.run(
                ["git", "clone", "--quiet", url, local_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
    except Exception as e:
        logger.error(f"Git operation failed for {url}: {e}")
        return False


def _index_all_repositories():
    """Index all registered repositories."""
    from core.database import get_repositories, update_repository_indexed
    from core.rag_service import get_rag_service
    
    repos = get_repositories(active_only=True)
    if not repos:
        logger.info("No repositories registered for indexing")
        return
    
    rag = get_rag_service()
    
    for repo in repos:
        repo_id = repo["id"]
        url = repo["url"]
        name = repo["name"] or url.split("/")[-1].replace(".git", "")
        
        # Determine local path
        local_path = os.path.join(REPOS_DIR, name)
        
        logger.info(f"Processing repository: {name} ({url})")
        
        # Clone or pull
        if _clone_or_pull_repo(url, local_path):
            # Index repository
            try:
                indexed_count = rag.index_repository(local_path, name)
                update_repository_indexed(repo_id, local_path)
                logger.info(f"Indexed {indexed_count} chunks from {name}")
            except Exception as e:
                logger.error(f"Indexing failed for {name}: {e}")
        else:
            logger.error(f"Failed to clone/pull {name}")


def _scheduler_loop():
    """Main scheduler loop running in background thread."""
    global _scheduler_running
    
    logger.info("RAG Scheduler started")
    
    # Initial indexing on startup (with delay to let other services initialize)
    time.sleep(5)
    logger.info("Starting initial indexing...")
    _index_all_repositories()
    
    # Periodic indexing
    while _scheduler_running:
        # Sleep for index interval
        for _ in range(INDEX_INTERVAL_MINUTES * 60):
            if not _scheduler_running:
                break
            time.sleep(1)
        
        if _scheduler_running:
            logger.info("Starting periodic indexing...")
            try:
                _index_all_repositories()
            except Exception as e:
                logger.error(f"Periodic indexing failed: {e}")
    
    logger.info("RAG Scheduler stopped")


def start_rag_scheduler():
    """Start the RAG scheduler background thread."""
    global _scheduler_thread, _scheduler_running
    
    if _scheduler_running:
        logger.info("RAG Scheduler already running")
        return
    
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()
    logger.info("RAG Scheduler thread started")


def stop_rag_scheduler():
    """Stop the RAG scheduler."""
    global _scheduler_running
    _scheduler_running = False
    logger.info("RAG Scheduler stopping...")


def trigger_indexing():
    """Manually trigger indexing of all repositories."""
    logger.info("Manual indexing triggered")
    threading.Thread(target=_index_all_repositories, daemon=True).start()
