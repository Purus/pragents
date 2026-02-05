"""Base agent interface for all agents."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum

from ..utils.logger import get_logger


class AgentStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentResult:
    """Result from agent execution."""

    def __init__(
        self,
        status: AgentStatus,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize agent result.

        Args:
            status: Execution status
            data: Result data
            error:  Error message if failed
            metadata: Additional metadata
        """
        self.status = status
        self.data = data or {}
        self.error = error
        self.metadata = metadata or {}

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == AgentStatus.SUCCESS

    def __repr__(self) -> str:
        return f"AgentResult(status={self.status.value}, data={len(self.data)} items)"


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: Optional[str] = None, **kwargs: Any):
        """
        Initialize base agent.

        Args:
            name: Agent name (defaults to class name)
            **kwargs: Agent-specific configuration
        """
        self.name = name or self.__class__.__name__
        self.config = kwargs
        self.logger = get_logger(f"agent.{self.name}")
        self.logger.info(f"Initialized {self.name}")

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's task.

        Args:
            context: Execution context with necessary data

        Returns:
            AgentResult with execution outcome

        Raises:
            AgentError: If execution fails critically
        """
        pass

    def validate_context(self, context: Dict[str, Any], required_keys: list[str]) -> None:
        """
        Validate that required keys are present in context.

        Args:
            context: Context dictionary to validate
            required_keys: List of required keys

        Raises:
            ValueError: If any required key is missing
        """
        missing_keys = [key for key in required_keys if key not in context]
        if missing_keys:
            raise ValueError(
                f"{self.name} missing required context keys: {', '.join(missing_keys)}"
            )

    def run(self, context: Dict[str, Any]) -> AgentResult:
        """
        Run the agent with error handling and logging.

        Args:
            context: Execution context

        Returns:
            AgentResult
        """
        self.logger.info(f"Starting {self.name}")
        try:
            result = self.execute(context)
            if result.is_success():
                self.logger.info(f"{self.name} completed successfully")
            else:
                self.logger.warning(f"{self.name} completed with status: {result.status.value}")
            return result
        except Exception as e:
            self.logger.error(f"{self.name} failed: {e}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                error=str(e),
                metadata={"exception_type": type(e).__name__}
            )


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass
