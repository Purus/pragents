"""Status and health check routes."""
from fastapi import APIRouter
from ..models import HealthResponse

router = APIRouter(tags=["status"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0"
    )


@router.get("/status")
async def system_status():
    """Get system status."""
    return {
        "status": "operational",
        "services": {
            "workflow": "running",
            "api": "running",
        }
    }
