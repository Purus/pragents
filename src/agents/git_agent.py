"""Git agent for repository operations using Azure DevOps."""
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

import git

from .base_agent import BaseAgent, AgentResult, AgentStatus, AgentError
from ..utils.helpers import sanitize_branch_name


class GitAgent(BaseAgent):
    """Agent for Git operations with Azure DevOps support."""

    def __init__(
        self,
        organization_url: str,
        project: str,
        token: str,
        base_branch: str = "main",
        branch_prefix: str = "coverage-improvement",
        **kwargs: Any
    ):
        """
        Initialize Git agent.

        Args:
            organization_url: Azure DevOps organization URL
            project: Project name
            token: Personal Access Token
            base_branch: Base branch name
            branch_prefix: Prefix for new branches
        """
        super().__init__(**kwargs)
        self.organization_url = organization_url
        self.project = project
        self.token = token
        self.base_branch = base_branch
        self.branch_prefix = branch_prefix
        self.repo: Optional[git.Repo] = None
        self.repo_path: Optional[Path] = None

    def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Execute Git operations based on context.

        Expected context keys:
            - operation: 'clone', 'create_branch', 'commit', 'push'
            - repo_url: Repository URL (for clone)
            - local_path: Local path for repository
            - branch_name: Branch name (optional, generated if not provided)
            - commit_message: Commit message (for commit)
            - files_to_add: List of file paths to stage (for commit)

        Returns:
            AgentResult with operation outcome
        """
        operation = context.get("operation", "clone")
        
        try:
            if operation == "clone":
                return self._clone_repository(context)
            elif operation == "create_branch":
                return self._create_branch(context)
            elif operation == "commit":
                return self._commit_changes(context)
            elif operation == "push":
                return self._push_changes(context)
            else:
                raise AgentError(f"Unknown operation: {operation}")
        except Exception as e:
            self.logger.error(f"Git operation '{operation}' failed: {e}")
            raise

    def _clone_repository(self, context: Dict[str, Any]) -> AgentResult:
        """Clone repository from Azure DevOps."""
        self.validate_context(context, ["repo_url", "local_path"])
        
        repo_url = context["repo_url"]
        local_path = Path(context["local_path"])

        # Add authentication to URL
        if "@" not in repo_url:
            # Insert token into URL
            if "https://" in repo_url:
                auth_url = repo_url.replace("https://", f"https://{self.token}@")
            else:
                auth_url = repo_url
        else:
            auth_url = repo_url

        try:
            # Remove existing directory if it exists
            if local_path.exists():
                self.logger.warning(f"Removing existing directory: {local_path}")
                shutil.rmtree(local_path)

            self.logger.info(f"Cloning repository to {local_path}")
            self.repo = git.Repo.clone_from(auth_url, local_path, branch=self.base_branch)
            self.repo_path = local_path

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "repo_path": str(local_path),
                    "current_branch": self.base_branch,
                },
                metadata={"operation": "clone"}
            )
        except git.GitCommandError as e:
            raise AgentError(f"Failed to clone repository: {e}")

    def _create_branch(self, context: Dict[str, Any]) -> AgentResult:
        """Create a new branch for changes."""
        if not self.repo:
            raise AgentError("Repository not initialized. Run clone operation first.")

        branch_name = context.get("branch_name")
        if not branch_name:
            # Generate branch name
            timestamp = context.get("timestamp", "")
            branch_name = f"{self.branch_prefix}-{timestamp}"
            branch_name = sanitize_branch_name(branch_name)

        try:
            # Create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            self.logger.info(f"Created and checked out branch: {branch_name}")

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={"branch_name": branch_name},
                metadata={"operation": "create_branch"}
            )
        except git.GitCommandError as e:
            raise AgentError(f"Failed to create branch: {e}")

    def _commit_changes(self, context: Dict[str, Any]) -> AgentResult:
        """Commit changes to the repository."""
        if not self.repo:
            raise AgentError("Repository not initialized. Run clone operation first.")

        self.validate_context(context, ["commit_message"])

        commit_message = context["commit_message"]
        files_to_add = context.get("files_to_add", [])

        try:
            # Add files
            if files_to_add:
                self.repo.index.add(files_to_add)
            else:
                # Add all changes
                self.repo.git.add(A=True)

            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD"):
                self.logger.info("No changes to commit")
                return AgentResult(
                    status=AgentStatus.SKIPPED,
                    data={"message": "No changes to commit"},
                    metadata={"operation": "commit"}
                )

            # Commit
            commit = self.repo.index.commit(commit_message)
            self.logger.info(f"Committed changes: {commit.hexsha[:7]}")

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "commit_sha": commit.hexsha,
                    "commit_message": commit_message,
                },
                metadata={"operation": "commit"}
            )
        except git.GitCommandError as e:
            raise AgentError(f"Failed to commit changes: {e}")

    def _push_changes(self, context: Dict[str, Any]) -> AgentResult:
        """Push changes to remote repository."""
        if not self.repo:
            raise AgentError("Repository not initialized. Run clone operation first.")

        try:
            current_branch = self.repo.active_branch.name
            origin = self.repo.remote("origin")
            
            self.logger.info(f"Pushing branch {current_branch} to origin")
            origin.push(current_branch)

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={"pushed_branch": current_branch},
                metadata={"operation": "push"}
            )
        except git.GitCommandError as e:
            raise AgentError(f"Failed to push changes: {e}")
