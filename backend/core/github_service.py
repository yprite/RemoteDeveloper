"""
GitHub Service Module - Handles GitHub API operations for PR creation and review management.
"""
import os
import time
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("github_service")


class GitHubService:
    """Service for interacting with GitHub API."""
    
    def __init__(self, token: Optional[str] = None, repo_owner: Optional[str] = None, repo_name: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def set_repo(self, owner: str, name: str):
        """Set the repository for operations."""
        self.repo_owner = owner
        self.repo_name = name
    
    def create_pull_request(
        self, 
        title: str, 
        body: str, 
        head: str, 
        base: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new pull request.
        
        Args:
            title: PR title
            body: PR description
            head: Source branch (e.g., feature/evt_123)
            base: Target branch (default: main)
        
        Returns:
            PR data dict or None on failure
        """
        if not self.token:
            logger.error("GitHub token not configured")
            return None
        
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code == 201:
                pr_data = response.json()
                logger.info(f"Created PR #{pr_data['number']}: {title}")
                return pr_data
            elif response.status_code == 422:
                # PR might already exist
                error_msg = response.json().get("errors", [{}])[0].get("message", "")
                if "A pull request already exists" in error_msg:
                    logger.info(f"PR already exists for {head}")
                    return self.get_pull_request_by_branch(head)
                logger.error(f"Failed to create PR: {response.json()}")
                return None
            else:
                logger.error(f"GitHub API error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return None
    
    def get_pull_request_by_branch(self, head: str) -> Optional[Dict[str, Any]]:
        """Get a PR by its head branch."""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"
        params = {"head": f"{self.repo_owner}:{head}", "state": "open"}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            if response.status_code == 200:
                prs = response.json()
                return prs[0] if prs else None
            return None
        except Exception as e:
            logger.error(f"Failed to get PR: {e}")
            return None
    
    def get_pr_reviews(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get all reviews for a PR."""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/reviews"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Failed to get reviews: {e}")
            return []
    
    def get_pr_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get all comments for a PR."""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/comments"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Failed to get comments: {e}")
            return []
    
    def get_pr_status(self, pr_number: int) -> Optional[str]:
        """
        Get PR status: 'open', 'closed', 'merged'.
        """
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                pr = response.json()
                if pr.get("merged"):
                    return "merged"
                return pr.get("state", "unknown")
            return None
        except Exception as e:
            logger.error(f"Failed to get PR status: {e}")
            return None
    
    def add_pr_comment(self, pr_number: int, body: str) -> bool:
        """Add a comment to a PR."""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{pr_number}/comments"
        
        try:
            response = requests.post(url, json={"body": body}, headers=self.headers, timeout=30)
            return response.status_code == 201
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return False
    
    def push_branch(self, local_path: str, branch: str) -> bool:
        """Push a local branch to remote."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                logger.info(f"Pushed branch {branch}")
                return True
            else:
                logger.error(f"Failed to push: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Push failed: {e}")
            return False
    
    def has_changes_requested(self, pr_number: int) -> bool:
        """Check if any review has requested changes."""
        reviews = self.get_pr_reviews(pr_number)
        for review in reviews:
            if review.get("state") == "CHANGES_REQUESTED":
                return True
        return False
    
    def get_pending_review_comments(self, pr_number: int) -> List[str]:
        """Get all unresolved review comments."""
        reviews = self.get_pr_reviews(pr_number)
        comments = []
        
        for review in reviews:
            if review.get("state") in ["CHANGES_REQUESTED", "COMMENTED"]:
                if review.get("body"):
                    comments.append(review["body"])
        
        # Also get line-level comments
        pr_comments = self.get_pr_comments(pr_number)
        for comment in pr_comments:
            if comment.get("body"):
                comments.append(comment["body"])
        
        return comments
    
    def wait_for_pr_close(
        self, 
        pr_number: int, 
        poll_interval: int = 10, 
        timeout: int = 3600
    ) -> str:
        """
        Poll until PR is closed/merged or timeout.
        
        Returns: 'merged', 'closed', or 'timeout'
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_pr_status(pr_number)
            
            if status == "merged":
                logger.info(f"PR #{pr_number} was merged")
                return "merged"
            elif status == "closed":
                logger.info(f"PR #{pr_number} was closed without merge")
                return "closed"
            
            time.sleep(poll_interval)
        
        logger.warning(f"Timeout waiting for PR #{pr_number}")
        return "timeout"


# Singleton instance
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    """Get the singleton GitHub service instance."""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service
