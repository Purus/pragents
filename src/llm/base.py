"""Base interface for LLM providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standard LLM response format."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, **kwargs: Any):
        """
        Initialize the LLM provider.

        Args:
            **kwargs: Provider-specific configuration
        """
        self.config = kwargs

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt
            system_message: Optional system message for context
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse containing the generated text

        Raises:
            LLMError: If generation fails
        """
        pass

    @abstractmethod
    def generate_with_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_message: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a JSON schema.

        Args:
            prompt: The input prompt
            schema: JSON schema for the expected output
            system_message: Optional system message
            **kwargs: Additional parameters

        Returns:
            Dictionary matching the provided schema

        Raises:
            LLMError: If generation fails or output doesn't match schema
        """
        pass

    def _validate_config(self, required_keys: list[str]) -> None:
        """
        Validate that required configuration keys are present.

        Args:
            required_keys: List of required configuration keys

        Raises:
            ValueError: If any required key is missing
        """
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            raise ValueError(
                f"Missing required configuration keys: {', '.join(missing_keys)}"
            )


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication fails."""
    pass


class LLMValidationError(LLMError):
    """Raised when output validation fails."""
    pass
