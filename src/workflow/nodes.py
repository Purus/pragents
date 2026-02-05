"""Workflow node implementations."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .state import WorkflowState
from ..agents import (
    GitAgent,
    SonarQubeAgent,
    AnalyzerAgent,
    TestGeneratorAgent,
    PRAzureDevOpsAgent
)
from ..llm import LLMFactory
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


def clone_repository_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Clone the target repository."""
    logger.info("Node: Cloning repository")
    
    settings = get_settings()
    
    git_agent = GitAgent(
        organization_url=settings.git.organization_url,
        project=settings.git.project,
        token=settings.git.token,
        base_branch=settings.git.base_branch,
        branch_prefix=settings.git.branch_prefix,
    )
    
    # Generate local path
    repo_name = state["repo_url"].split("/")[-1].replace(".git", "")
    local_path = Path("./workspaces") / repo_name
    
    result = git_agent.run({
        "operation": "clone",
        "repo_url": state["repo_url"],
        "local_path": str(local_path),
    })
    
    if result.is_success():
        return {
            "repo_path": result.data["repo_path"],
            "current_step": "clone",
            "repository_id": repo_name,
        }
    else:
        return {
            "errors": [result.error],
            "status": "failed",
            "current_step": "clone",
        }


def check_coverage_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Check current code coverage from SonarQube."""
    logger.info("Node: Checking coverage")
    
    settings = get_settings()
    
    sonar_agent = SonarQubeAgent(
        sonar_url=settings.sonarqube.url,
        sonar_token=settings.sonarqube.token,
    )
    
    result = sonar_agent.run({
        "project_key": state["sonar_project_key"],
    })
    
    if result.is_success():
        coverage = result.data["coverage"]
        return {
            "coverage_before": coverage,
            "coverage_metrics": result.data["metrics"],
            "uncovered_files": result.data["uncovered_files"],
            "current_step": "check_coverage",
        }
    else:
        return {
            "errors": [result.error],
            "status": "failed",
            "current_step": "check_coverage",
        }


def should_generate_tests(state: WorkflowState) -> str:
    """Decision node: Determine if tests need to be generated."""
    coverage = state.get("coverage_before", 0)
    threshold = state.get("coverage_threshold", 90)
    
    if coverage < threshold:
        logger.info(f"Coverage {coverage}% < {threshold}%, proceeding with test generation")
        return "analyze_code"
    else:
        logger.info(f"Coverage {coverage}% >= {threshold}%, skipping test generation")
        return "end"


def analyze_code_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Analyze code to identify test candidates."""
    logger.info("Node: Analyzing code")
    
    settings = get_settings()
    
    analyzer_agent = AnalyzerAgent(
        exclude_patterns=settings.code_analysis.exclude_patterns,
        min_function_lines=settings.code_analysis.min_function_lines,
    )
    
    result = analyzer_agent.run({
        "repo_path": state["repo_path"],
        "uncovered_files": state.get("uncovered_files", []),
    })
    
    if result.is_success():
        return {
            "test_candidates": result.data["test_candidates"],
            "current_step": "analyze_code",
        }
    else:
        return {
            "errors": [result.error],
            "status": "failed",
            "current_step": "analyze_code",
        }


def generate_tests_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Generate unit tests using LLM."""
    logger.info("Node: Generating tests")
    
    settings = get_settings()
    
    # Create LLM provider
    llm = LLMFactory.create_from_config(settings.llm)
    
    test_gen_agent = TestGeneratorAgent(
        llm_provider=llm,
        test_framework=settings.test_generation.framework,
        test_directory=settings.test_generation.test_directory,
    )
    
    result = test_gen_agent.run({
        "test_candidates": state["test_candidates"],
        "repo_path": state["repo_path"],
        "max_tests": settings.workflow.max_tests_per_file,
    })
    
    if result.is_success():
        return {
            "generated_tests": result.data["generated_tests"],
            "test_files": result.data["test_files"],
            "current_step": "generate_tests",
        }
    else:
        return {
            "errors": [result.error],
            "status": "failed",
            "current_step": "generate_tests",
        }


def create_pr_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Commit changes and create pull request."""
    logger.info("Node: Creating PR")
    
    settings = get_settings()
    
    # First, commit and push changes
    git_agent = GitAgent(
        organization_url=settings.git.organization_url,
        project=settings.git.project,
        token=settings.git.token,
        base_branch=settings.git.base_branch,
        branch_prefix=settings.git.branch_prefix,
    )
    
    # Create branch
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_result = git_agent.run({
        "operation": "create_branch",
        "branch_name": f"{settings.git.branch_prefix}-{timestamp}",
        "timestamp": timestamp,
    })
    
    if not branch_result.is_success():
        return {"errors": [branch_result.error], "status": "failed", "current_step": "create_pr"}
    
    branch_name = branch_result.data["branch_name"]
    
    # Commit changes
    commit_result = git_agent.run({
        "operation": "commit",
        "commit_message": "Add generated unit tests to improve code coverage",
        "files_to_add": state["test_files"],
    })
    
    if not commit_result.is_success() and commit_result.status.value != "skipped":
        return {"errors": [commit_result.error], "status": "failed", "current_step": "create_pr"}
    
    # Push changes
    push_result = git_agent.run({
        "operation": "push",
    })
    
    if not push_result.is_success():
        return {"errors": [push_result.error], "status": "failed", "current_step": "create_pr"}
    
    # Create PR
    pr_agent = PRAzureDevOpsAgent(
        organization_url=settings.git.organization_url,
        project=settings.git.project,
        token=settings.git.token,
        base_branch=settings.git.base_branch,
    )
    
    pr_result = pr_agent.run({
        "repository_id": state["repository_id"],
        "source_branch": branch_name,
        "pr_title": f"Improve code coverage - {timestamp}",
        "pr_description": "Automated code coverage improvement with generated unit tests",
        "test_files": state["test_files"],
        "coverage_before": state.get("coverage_before"),
    })
    
    if pr_result.is_success():
        return {
            "branch_name": branch_name,
            "pr_id": pr_result.data["pr_id"],
            "pr_url": pr_result.data["pr_url"],
            "status": "success",
            "current_step": "create_pr",
        }
    else:
        return {
            "errors": [pr_result.error],
            "status": "failed",
            "current_step": "create_pr",
        }
