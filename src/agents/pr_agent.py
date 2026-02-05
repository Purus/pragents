"""PR agent for creating pull requests in Azure DevOps."""
from typing import Dict, Any, List
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_0.git.models import GitPullRequest, GitPullRequestSearchCriteria

from .base_agent import BaseAgent, AgentResult, AgentStatus, AgentError


class PRAzureDevOpsAgent(BaseAgent):
    """Agent for creating pull requests in Azure DevOps."""

    def __init__(
        self,
        organization_url: str,
        project: str,
        token: str,
        base_branch: str = "main",
        **kwargs: Any
    ):
        """
        Initialize PR agent.

        Args:
            organization_url: Azure DevOps organization URL
            project: Project name
            token: Personal Access Token
            base_branch: Base branch for PRs
        """
        super().__init__(**kwargs)
        self.organization_url = organization_url
        self.project = project
        self.token = token
        self.base_branch = base_branch
        
        # Initialize Azure DevOps connection
        credentials = BasicAuthentication('', token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
        self.git_client = self.connection.clients.get_git_client()

    def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Create a pull request with generated tests.

        Expected context keys:
            - repository_id: Repository ID or name
            - source_branch: Source branch with changes
            - pr_title: Pull request title
            - pr_description: Pull request description (optional)
            - test_files: List of test files created

        Returns:
            AgentResult with PR information
        """
        self.validate_context(context, ["repository_id", "source_branch", "pr_title"])
        
        repository_id = context["repository_id"]
        source_branch = context["source_branch"]
        pr_title = context["pr_title"]
        pr_description = context.get("pr_description", "")
        test_files = context.get("test_files", [])

        try:
            # Build PR description
            full_description = self._build_pr_description(
                pr_description,
                test_files,
                context.get("coverage_before"),
                context.get("coverage_after")
            )

            # Create pull request
            pr = GitPullRequest(
                source_ref_name=f"refs/heads/{source_branch}",
                target_ref_name=f"refs/heads/{self.base_branch}",
                title=pr_title,
                description=full_description
            )

            self.logger.info(f"Creating PR: {pr_title}")
            created_pr = self.git_client.create_pull_request(
                git_pull_request_to_create=pr,
                repository_id=repository_id,
                project=self.project
            )

            pr_url = f"{self.organization_url}/{self.project}/_git/{repository_id}/pullrequest/{created_pr.pull_request_id}"
            
            self.logger.info(f"Created PR #{created_pr.pull_request_id}: {pr_url}")

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "pr_id": created_pr.pull_request_id,
                    "pr_url": pr_url,
                    "source_branch": source_branch,
                    "target_branch": self.base_branch,
                    "title": pr_title,
                },
                metadata={"repository": repository_id}
            )
        except Exception as e:
            self.logger.error(f"Failed to create PR: {e}")
            raise AgentError(f"PR creation failed: {e}")

    def _build_pr_description(
        self,
        description: str,
        test_files: List[str],
        coverage_before: float = None,
        coverage_after: float = None
    ) -> str:
        """Build comprehensive PR description."""
        lines = []
        
        if description:
            lines.append(description)
            lines.append("")
        
        lines.append("## 🤖 Automated Code Coverage Improvement")
        lines.append("")
        lines.append("This pull request was automatically generated to improve code coverage.")
        lines.append("")

        if coverage_before is not None:
            lines.append("### Coverage Metrics")
            lines.append(f"- **Before**: {coverage_before:.1f}%")
            if coverage_after is not None:
                lines.append(f"- **After**: {coverage_after:.1f}%")
                improvement = coverage_after - coverage_before
                lines.append(f"- **Improvement**: +{improvement:.1f}%")
            lines.append("")

        if test_files:
            lines.append(f"### Generated Test Files ({len(test_files)})")
            for test_file in test_files:
                lines.append(f"- `{test_file}`")
            lines.append("")

        lines.append("### Review Checklist")
        lines.append("- [ ] Tests are comprehensive and cover edge cases")
        lines.append("- [ ] All tests pass locally")
        lines.append("- [ ] No breaking changes introduced")
        lines.append("- [ ] Code follows project style guidelines")
        lines.append("")
        lines.append("---")
        lines.append("*Generated by Code Coverage Agent*")

        return "\n".join(lines)
