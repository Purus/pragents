"""Workflow API routes."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
import uuid
from typing import Dict

from ..models import WorkflowStartRequest, WorkflowStartResponse, WorkflowStatusResponse, WorkflowStatus
from ...workflow import compiled_workflow
from ...utils.logger import get_logger

router = APIRouter(prefix="/workflow", tags=["workflow"])
logger = get_logger(__name__)

# In-memory workflow tracking (in production, use database)
workflows: Dict[str, Dict] = {}


async def run_workflow_background(workflow_id: str, request: WorkflowStartRequest):
    """Run workflow in background."""
    try:
        workflows[workflow_id]["status"] = WorkflowStatus.RUNNING
        
        initial_state = {
            "repo_url": request.repo_url,
            "sonar_project_key": request.sonar_project_key,
            "coverage_threshold": request.coverage_threshold,
            "timestamp": datetime.now().isoformat(),
            "workflow_id": workflow_id,
            "errors": [],
        }
        
        logger.info(f"Starting workflow {workflow_id}")
        result = compiled_workflow.invoke(initial_state)
        
        # Update workflow status
        workflows[workflow_id].update({
            "status": WorkflowStatus.SUCCESS if result.get("status") != "failed" else WorkflowStatus.FAILED,
            "current_step": result.get("current_step"),
            "coverage_before": result.get("coverage_before"),
            "pr_url": result.get("pr_url"),
            "errors": result.get("errors", []),
            "result": result,
        })
        
        logger.info(f"Workflow {workflow_id} completed with status: {workflows[workflow_id]['status']}")
    except Exception as e:
        logger.error(f"Workflow {workflow_id} failed: {e}")
        workflows[workflow_id].update({
            "status": WorkflowStatus.FAILED,
            "errors": [str(e)],
        })


@router.post("/start", response_model=WorkflowStartResponse)
async def start_workflow(request: WorkflowStartRequest, background_tasks: BackgroundTasks):
    """Start a new workflow."""
    workflow_id = str(uuid.uuid4())
    
    # Initialize workflow tracking
    workflows[workflow_id] = {
        "workflow_id": workflow_id,
        "status": WorkflowStatus.PENDING,
        "created_at": datetime.now().isoformat(),
        "request": request.dict(),
    }
    
    # Run workflow in background
    background_tasks.add_task(run_workflow_background, workflow_id, request)
    
    return WorkflowStartResponse(
        workflow_id=workflow_id,
        status=WorkflowStatus.PENDING,
        message="Workflow started successfully"
    )


@router.get("/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """Get workflow status."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    
    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        status=workflow["status"],
        current_step=workflow.get("current_step"),
        coverage_before=workflow.get("coverage_before"),
        pr_url=workflow.get("pr_url"),
        errors=workflow.get("errors", []),
        created_at=workflow["created_at"],
    )


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # In a real implementation, you'd need to implement cancellation logic
    # For now, just mark as failed
    workflows[workflow_id]["status"] = WorkflowStatus.FAILED
    workflows[workflow_id]["errors"] = ["Cancelled by user"]
    
    return {"message": "Workflow cancelled"}


@router.get("/")
async def list_workflows():
    """List all workflows."""
    return {"workflows": list(workflows.values())}
