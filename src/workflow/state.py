"""Workflow state definition."""
from typing import TypedDict, List, Dict, Any, Optional


class WorkflowState(TypedDict, total=False):
    """State for the code coverage workflow."""
    
    # Input parameters
    repo_url: str
    sonar_project_key: str
    coverage_threshold: int
    
    # Repository information
    repo_path: str
    repository_id: str
    
    # Coverage data
    coverage_before: float
    coverage_metrics: Dict[str, float]
    uncovered_files: List[Dict[str, Any]]
    
    # Analysis results
    test_candidates: List[Dict[str, Any]]
    
    # Generated content
    generated_tests: List[Dict[str, Any]]
    test_files: List[str]
    
    # Branch and PR information
    branch_name: str
    pr_id: Optional[int]
    pr_url: Optional[str]
    
    # Execution metadata
    status: str
    errors: List[str]
    current_step: str
    
    # Optional fields for checkpointing
    timestamp: str
    workflow_id: Optional[str]
