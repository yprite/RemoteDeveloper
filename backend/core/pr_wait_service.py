"""
PR Wait Service - Manages PR status polling and agent resumption.

Handles:
- Marking events as PENDING_PR_CLOSE
- Polling PR status periodically
- Resuming agent progression when PR is merged/closed
"""
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("pr_wait_service")


@dataclass
class PendingPR:
    """Represents a PR waiting for close/merge."""
    event_id: str
    pr_number: int
    repo_owner: str
    repo_name: str
    agent_name: str
    next_agent: str
    event_data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    last_checked: Optional[datetime] = None
    status: str = "pending"  # pending, merged, closed, timeout


class PrWaitService:
    """
    Service for managing PR close/merge waiting.
    
    Agents register PRs they're waiting on, and this service
    polls GitHub and triggers continuation when PRs are merged.
    """
    
    def __init__(self, poll_interval: int = 30, timeout_hours: int = 24):
        self._pending: Dict[str, PendingPR] = {}  # event_id -> PendingPR
        self._poll_interval = poll_interval
        self._timeout_seconds = timeout_hours * 3600
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_pr_merged: Optional[Callable[[PendingPR], None]] = None
        self._on_changes_requested: Optional[Callable] = None
    
    def register_pr_wait(
        self,
        event_id: str,
        pr_number: int,
        repo_owner: str,
        repo_name: str,
        agent_name: str,
        next_agent: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Register a PR to wait for.
        
        Args:
            event_id: Unique event identifier
            pr_number: GitHub PR number
            repo_owner: Repository owner
            repo_name: Repository name
            agent_name: Current agent that created the PR
            next_agent: Agent to trigger when PR is merged
            event_data: Full event data to pass to next agent
        """
        self._pending[event_id] = PendingPR(
            event_id=event_id,
            pr_number=pr_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            agent_name=agent_name,
            next_agent=next_agent,
            event_data=event_data
        )
        logger.info(f"Registered PR wait: event={event_id}, PR=#{pr_number}, waiting for merge before {next_agent}")
    
    def check_pr_status(self, pending: PendingPR) -> str:
        """Check current status of a PR."""
        from core.github_service import get_github_service
        
        github = get_github_service()
        github.set_repo(pending.repo_owner, pending.repo_name)
        
        status = github.get_pr_status(pending.pr_number)
        pending.last_checked = datetime.now()
        
        return status or "unknown"
    
    def poll_once(self) -> List[PendingPR]:
        """
        Poll all pending PRs once.
        
        Returns list of PRs that are now merged/closed.
        Also checks for review feedback and triggers rework if needed.
        """
        from core.pr_review_service import get_pr_review_service
        
        completed = []
        review_service = get_pr_review_service()
        
        for event_id, pending in list(self._pending.items()):
            try:
                # Check timeout
                age = (datetime.now() - pending.created_at).total_seconds()
                if age > self._timeout_seconds:
                    pending.status = "timeout"
                    completed.append(pending)
                    logger.warning(f"PR wait timeout: event={event_id}, PR=#{pending.pr_number}")
                    continue
                
                # Check for review feedback first
                feedback = review_service.get_pending_feedback(
                    pending.pr_number, 
                    pending.repo_owner, 
                    pending.repo_name
                )
                if feedback:
                    logger.info(f"Changes requested on PR #{pending.pr_number}")
                    # Trigger rework callback
                    if self._on_changes_requested:
                        try:
                            self._on_changes_requested(pending, feedback)
                        except Exception as e:
                            logger.error(f"Error in rework callback: {e}")
                    continue  # Don't remove from pending - wait for re-push
                
                # Check PR status
                status = self.check_pr_status(pending)
                
                if status == "merged":
                    pending.status = "merged"
                    completed.append(pending)
                    logger.info(f"PR merged: event={event_id}, PR=#{pending.pr_number}")
                elif status == "closed":
                    pending.status = "closed"
                    completed.append(pending)
                    logger.info(f"PR closed (not merged): event={event_id}, PR=#{pending.pr_number}")
                    
            except Exception as e:
                logger.error(f"Error checking PR status ({event_id}): {e}")
        
        # Remove completed PRs from pending
        for pending in completed:
            del self._pending[pending.event_id]
            
            # Trigger callback if registered
            if self._on_pr_merged and pending.status == "merged":
                try:
                    self._on_pr_merged(pending)
                except Exception as e:
                    logger.error(f"Error in PR merged callback: {e}")
        
        return completed
    
    def set_merged_callback(self, callback: Callable[[PendingPR], None]) -> None:
        """Set callback to trigger when PR is merged."""
        self._on_pr_merged = callback
    
    def set_changes_requested_callback(self, callback: Callable) -> None:
        """Set callback to trigger when changes are requested on a PR."""
        self._on_changes_requested = callback
    
    def start_polling(self) -> None:
        """Start background polling thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("PR wait polling started")
    
    def stop_polling(self) -> None:
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("PR wait polling stopped")
    
    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            if self._pending:
                self.poll_once()
            time.sleep(self._poll_interval)
    
    def get_pending_prs(self) -> List[Dict[str, Any]]:
        """Get list of all pending PRs."""
        return [
            {
                "event_id": p.event_id,
                "pr_number": p.pr_number,
                "agent": p.agent_name,
                "next_agent": p.next_agent,
                "repo": f"{p.repo_owner}/{p.repo_name}",
                "created_at": p.created_at.isoformat(),
                "last_checked": p.last_checked.isoformat() if p.last_checked else None
            }
            for p in self._pending.values()
        ]
    
    def is_event_pending(self, event_id: str) -> bool:
        """Check if an event is waiting for PR."""
        return event_id in self._pending


# Singleton instance
_pr_wait_service: Optional[PrWaitService] = None


def get_pr_wait_service() -> PrWaitService:
    """Get the singleton PR wait service instance."""
    global _pr_wait_service
    if _pr_wait_service is None:
        _pr_wait_service = PrWaitService()
    return _pr_wait_service
