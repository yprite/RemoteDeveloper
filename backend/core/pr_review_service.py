"""
PR Review Service - Handles PR review detection and rework triggering.

Extends pr_wait_service with review handling capabilities:
- Detect CHANGES_REQUESTED reviews
- Fetch review comments
- Trigger agent rework based on feedback
- Re-submit changes to PR
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("pr_review_service")


class ReviewStatus(Enum):
    """PR review status types."""
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    PENDING = "PENDING"
    DISMISSED = "DISMISSED"


@dataclass
class ReviewFeedback:
    """Structured review feedback for agent rework."""
    pr_number: int
    reviewer: str
    status: ReviewStatus
    body: str
    comments: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[datetime] = None
    
    def get_formatted_feedback(self) -> str:
        """Format feedback for LLM consumption."""
        parts = [f"## PR #{self.pr_number} 리뷰 피드백"]
        parts.append(f"- 리뷰어: {self.reviewer}")
        parts.append(f"- 상태: {self.status.value}")
        
        if self.body:
            parts.append(f"\n### 리뷰 내용\n{self.body}")
        
        if self.comments:
            parts.append("\n### 라인별 코멘트")
            for comment in self.comments:
                path = comment.get("path", "unknown")
                line = comment.get("line", "?")
                body = comment.get("body", "")
                parts.append(f"\n**{path}:{line}**\n{body}")
        
        return "\n".join(parts)


class PrReviewService:
    """
    Service for PR review handling.
    
    Monitors PRs for review feedback and triggers agent rework
    when changes are requested.
    """
    
    def __init__(self):
        self._on_changes_requested: Optional[Callable[[str, ReviewFeedback], None]] = None
    
    def check_pr_reviews(self, pr_number: int, repo_owner: str, repo_name: str) -> List[ReviewFeedback]:
        """
        Check for reviews on a PR.
        
        Returns list of review feedback objects.
        """
        from core.github_service import get_github_service
        
        github = get_github_service()
        github.set_repo(repo_owner, repo_name)
        
        reviews = github.get_pr_reviews(pr_number)
        feedback_list = []
        
        for review in reviews:
            state = review.get("state", "PENDING")
            
            try:
                status = ReviewStatus[state]
            except KeyError:
                status = ReviewStatus.PENDING
            
            feedback = ReviewFeedback(
                pr_number=pr_number,
                reviewer=review.get("user", {}).get("login", "unknown"),
                status=status,
                body=review.get("body", ""),
                created_at=datetime.fromisoformat(review["submitted_at"].replace("Z", "+00:00")) if review.get("submitted_at") else None
            )
            feedback_list.append(feedback)
        
        # Also fetch line-level comments
        comments = github.get_pr_comments(pr_number)
        for comment in comments:
            # Attach to most recent feedback or create new one
            comment_data = {
                "path": comment.get("path", ""),
                "line": comment.get("line", comment.get("original_line")),
                "body": comment.get("body", "")
            }
            if feedback_list:
                feedback_list[-1].comments.append(comment_data)
        
        return feedback_list
    
    def has_changes_requested(self, pr_number: int, repo_owner: str, repo_name: str) -> bool:
        """Check if any review has requested changes."""
        feedbacks = self.check_pr_reviews(pr_number, repo_owner, repo_name)
        for fb in feedbacks:
            if fb.status == ReviewStatus.CHANGES_REQUESTED:
                return True
        return False
    
    def get_pending_feedback(self, pr_number: int, repo_owner: str, repo_name: str) -> Optional[ReviewFeedback]:
        """Get the most recent CHANGES_REQUESTED feedback."""
        feedbacks = self.check_pr_reviews(pr_number, repo_owner, repo_name)
        
        # Find most recent changes_requested
        for fb in reversed(feedbacks):
            if fb.status == ReviewStatus.CHANGES_REQUESTED:
                return fb
        
        return None
    
    def set_changes_requested_callback(self, callback: Callable[[str, ReviewFeedback], None]) -> None:
        """Set callback when changes are requested."""
        self._on_changes_requested = callback
    
    def trigger_rework(self, event_id: str, feedback: ReviewFeedback) -> None:
        """Trigger agent rework based on review feedback."""
        if self._on_changes_requested:
            self._on_changes_requested(event_id, feedback)
        else:
            logger.warning(f"No rework callback set for event {event_id}")
    
    def create_rework_event(
        self, 
        original_event: Dict[str, Any], 
        feedback: ReviewFeedback,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Create a rework event based on original event and feedback.
        
        The rework event includes the feedback context for the agent
        to understand what needs to be changed.
        """
        rework_event = original_event.copy()
        rework_event["is_rework"] = True
        rework_event["rework_feedback"] = feedback.get_formatted_feedback()
        rework_event["rework_agent"] = agent_name
        rework_event["status"] = "REWORK"
        
        # Add feedback to task context
        task = rework_event.get("task", {})
        task["rework_instructions"] = feedback.get_formatted_feedback()
        rework_event["task"] = task
        
        logger.info(f"Created rework event for {agent_name} based on PR #{feedback.pr_number} feedback")
        
        return rework_event


# Singleton instance
_pr_review_service: Optional[PrReviewService] = None


def get_pr_review_service() -> PrReviewService:
    """Get the singleton PR review service instance."""
    global _pr_review_service
    if _pr_review_service is None:
        _pr_review_service = PrReviewService()
    return _pr_review_service
