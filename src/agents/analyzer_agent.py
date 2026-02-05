"""Code analyzer agent for identifying test candidates."""
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent, AgentResult, AgentStatus, AgentError


class TestCandidate:
    """General test candidate information for any language."""
    def __init__(self, file_path: str, uncovered_area: Any, language: str):
        self.file_path = file_path
        self.uncovered_area = uncovered_area  # Could be line numbers, blocks, etc.
        self.language = language

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "uncovered_area": self.uncovered_area,
            "language": self.language,
        }

class AnalyzerAgent(BaseAgent):
    """Agent for analyzing code and identifying test candidates (multi-language)."""

    def __init__(self, **kwargs: Any):
        """
        Initialize analyzer agent.
        Args:
            kwargs: Additional arguments for BaseAgent
        """
        super().__init__(**kwargs)

    def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Analyze code to identify test candidates using SonarQube uncovered files.

        Expected context keys:
            - repo_path: Path to repository
            - uncovered_files: List of uncovered files/areas from SonarQube
                Each item should include: file path, uncovered area (lines/blocks), language

        Returns:
            AgentResult with test candidates
        """
        self.validate_context(context, ["repo_path", "uncovered_files"])
        repo_path = Path(context["repo_path"])
        uncovered_files = context["uncovered_files"]

        try:
            test_candidates = []
            for file_info in uncovered_files:
                file_path = str(repo_path / file_info["path"])
                uncovered_area = file_info.get("uncovered_area")
                language = file_info.get("language", "unknown")
                candidate = TestCandidate(file_path, uncovered_area, language)
                test_candidates.append(candidate)

            self.logger.info(f"Identified {len(test_candidates)} test candidates (multi-language)")

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "test_candidates": [c.to_dict() for c in test_candidates],
                    "total_candidates": len(test_candidates),
                },
                metadata={"analyzed_files": len(test_candidates)}
            )
        except Exception as e:
            self.logger.error(f"Code analysis failed: {e}")
            raise AgentError(f"Analysis error: {e}")
