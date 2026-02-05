"""SonarQube agent for fetching code coverage metrics."""
from typing import Dict, Any
from pathlib import Path

import requests

from .base_agent import BaseAgent, AgentResult, AgentStatus, AgentError


class SonarQubeAgent(BaseAgent):
    """Agent for interacting with SonarQube API."""

    def __init__(
        self,
        sonar_url: str,
        sonar_token: str,
        **kwargs: Any
    ):
        """
        Initialize SonarQube agent.

        Args:
            sonar_url: SonarQube server URL
            sonar_token: Authentication token
        """
        super().__init__(**kwargs)
        self.sonar_url = sonar_url.rstrip("/")
        self.sonar_token = sonar_token
        self.session = requests.Session()
        self.session.auth = (sonar_token, "")

    def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Fetch coverage metrics from SonarQube.

        Expected context keys:
            - project_key: SonarQube project key

        Returns:
            AgentResult with coverage data
        """
        self.validate_context(context, ["project_key"])
        project_key = context["project_key"]

        try:
            # Fetch project metrics
            metrics_data = self._fetch_metrics(project_key)
            
            # Fetch detailed coverage info
            coverage_details = self._fetch_coverage_details(project_key)

            coverage_value = metrics_data.get("coverage", 0.0)
            
            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "project_key": project_key,
                    "coverage": coverage_value,
                    "metrics": metrics_data,
                    "uncovered_lines": coverage_details.get("uncovered_lines", []),
                    "uncovered_files": coverage_details.get("uncovered_files", []),
                },
                metadata={"sonar_url": self.sonar_url}
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch SonarQube data: {e}")
            raise AgentError(f"SonarQube API error: {e}")

    def _fetch_metrics(self, project_key: str) -> Dict[str, float]:
        """Fetch project metrics from SonarQube."""
        url = f"{self.sonar_url}/api/measures/component"
        params = {
            "component": project_key,
            "metricKeys": "coverage,line_coverage,branch_coverage,lines_to_cover,uncovered_lines"
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            metrics = {}
            for measure in data.get("component", {}).get("measures", []):
                metric_key = measure["metric"]
                metric_value = float(measure.get("value", 0))
                metrics[metric_key] = metric_value

            self.logger.info(f"Fetched metrics for {project_key}: {metrics}")
            return metrics
        except requests.RequestException as e:
            raise AgentError(f"Failed to fetch metrics: {e}")

    def _fetch_coverage_details(self, project_key: str) -> Dict[str, Any]:
        """Fetch detailed coverage information."""
        # This is simplified - in production you'd fetch file-level coverage
        url = f"{self.sonar_url}/api/measures/component_tree"
        params = {
            "component": project_key,
            "metricKeys": "coverage,uncovered_lines",
            "qualifiers": "FIL",  # Files only
            "ps": 100,  # Page size
        }

        # Helper: infer language from file extension
        def infer_language(path: str) -> str:
            ext = Path(path).suffix.lower()
            return {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".java": "java",
                ".cs": "csharp",
                ".cpp": "cpp",
                ".c": "c",
                ".go": "go",
                ".rb": "ruby",
                ".php": "php",
                ".swift": "swift",
                ".kt": "kotlin",
                ".scala": "scala",
                ".rs": "rust",
                ".m": "objective-c",
                ".dart": "dart",
                ".pl": "perl",
                ".sh": "shell",
            }.get(ext, "unknown")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            uncovered_files = []
            for component in data.get("components", []):
                measures = {m["metric"]: m.get("value") for m in component.get("measures", [])}
                coverage = float(measures.get("coverage", 100))
                path = component["path"]
                language = component.get("language") or infer_language(path)
                if coverage < 100:  # Has uncovered lines
                    uncovered_files.append({
                        "path": path,
                        "coverage": coverage,
                        "uncovered_area": int(measures.get("uncovered_lines", 0)),
                        "language": language,
                    })

            self.logger.info(f"Found {len(uncovered_files)} files with incomplete coverage")
            return {
                "uncovered_files": uncovered_files,
                "uncovered_lines": sum(f["uncovered_area"] for f in uncovered_files),
            }
        except requests.RequestException as e:
            self.logger.warning(f"Failed to fetch coverage details: {e}")
            # Return empty data rather than failing
            return {"uncovered_files": [], "uncovered_lines": 0}
