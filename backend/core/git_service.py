import os
from typing import Optional, List
from git import Repo, GitCommandError
import logging

from core.logging_config import logger

class GitService:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._repo: Optional[Repo] = None

    def _ensure_repo(self):
        if not self._repo:
            if os.path.exists(os.path.join(self.repo_path, ".git")):
                self._repo = Repo(self.repo_path)
            else:
                pass # Repo not initialized yet

    def clone(self, url: str) -> bool:
        """Clone a repository to the initialized path."""
        try:
            if os.path.exists(self.repo_path) and os.listdir(self.repo_path):
                # Directory exists and not empty, check if it is a git repo
                if os.path.exists(os.path.join(self.repo_path, ".git")):
                    self._repo = Repo(self.repo_path)
                    logger.info(f"Repository already exists at {self.repo_path}")
                    return True
                else:
                    logger.warning(f"Directory {self.repo_path} exists and is not empty, but not a git repo.")
                    # For safety, don't delete. Just error.
                    return False
            
            logger.info(f"Cloning {url} to {self.repo_path}")
            self._repo = Repo.clone_from(url, self.repo_path)
            return True
        except GitCommandError as e:
            logger.error(f"Git clone error: {e}")
            raise e

    def checkout(self, branch_name: str, create_if_missing: bool = False) -> bool:
        """Checkout a branch, optionally creating it."""
        self._ensure_repo()
        if not self._repo:
            raise Exception("Repository not initialized")

        try:
            if branch_name in self._repo.heads:
                self._repo.heads[branch_name].checkout()
                logger.info(f"Checked out existing branch: {branch_name}")
            elif create_if_missing:
                new_branch = self._repo.create_head(branch_name)
                new_branch.checkout()
                logger.info(f"Created and checked out new branch: {branch_name}")
            else:
                logger.error(f"Branch {branch_name} not found")
                return False
            return True
        except GitCommandError as e:
            logger.error(f"Git checkout error: {e}")
            raise e

    def add_all(self):
        self._ensure_repo()
        self._repo.git.add('.')

    def commit(self, message: str) -> bool:
        """Commit changes."""
        self._ensure_repo()
        if not self._repo:
             raise Exception("Repository not initialized")
        
        try:
            if not self._repo.is_dirty(untracked_files=True):
                logger.info("No changes to commit")
                return False
            
            self._repo.git.add(A=True) # Add all
            self._repo.index.commit(message)
            logger.info(f"Committed with message: {message}")
            return True
        except GitCommandError as e:
            logger.error(f"Git commit error: {e}")
            raise e

    def push(self, branch_name: str, remote_name: str = "origin") -> bool:
        """Push changes to remote."""
        self._ensure_repo()
        if not self._repo:
             raise Exception("Repository not initialized")

        try:
            remote = self._repo.remote(name=remote_name)
            remote.push(refspec=f"{branch_name}:{branch_name}")
            logger.info(f"Pushed {branch_name} to {remote_name}")
            return True
        except GitCommandError as e:
            logger.error(f"Git push error: {e}")
            raise e

    def get_file_content(self, relative_path: str) -> Optional[str]:
        full_path = os.path.join(self.repo_path, relative_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def write_file_content(self, relative_path: str, content: str):
        full_path = os.path.join(self.repo_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
