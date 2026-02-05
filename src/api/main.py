"""FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import workflow, status
from ..config import get_settings
from ..utils.logger import setup_logger

# Setup logging
logger = setup_logger("api", level="INFO")

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Code Coverage Agent API",
    description="API for automated code coverage improvement",
    version="0.1.0",
    docs_url="/docs" if settings.api.enable_docs else None,
    redoc_url="/redoc" if settings.api.enable_docs else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflow.router, prefix="/api")
app.include_router(status.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting Code Coverage Agent API")
    logger.info(f"API running on {settings.api.host}:{settings.api.port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down Code Coverage Agent API")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Code Coverage Agent API",
        "version": "0.1.0",
        "docs": "/docs" if settings.api.enable_docs else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=True
    )
