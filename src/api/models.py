"""FastAPI request/response models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class WorkflowStartRequest(BaseModel):
    """Request to start a workflow."""
    repo_url: str = Field(..., description="Repository URL")
    sonar_project_key: str = Field(..., description="SonarQube project key")
    coverage_threshold: int = Field(default=90, ge=0, le=100, description="Coverage threshold")


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""
    workflow_id: str
    status: WorkflowStatus
    current_step: Optional[str] = None
    coverage_before: Optional[float] = None
    coverage_after: Optional[float] = None
    pr_url: Optional[str] = None
    errors: List[str] = []
    created_at: str


class WorkflowStartResponse(BaseModel):
    """Response after starting a workflow."""
    workflow_id: str
    status: WorkflowStatus
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
