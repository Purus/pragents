"""LLM provider factory."""
from typing import Any, Dict, Type

from .base import BaseLLMProvider, LLMError
from .providers.openai import OpenAIProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """Factory for creating LLM providers."""

    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        # Add more providers as they are implemented
        # "anthropic": AnthropicProvider,
        # "azure_openai": AzureOpenAIProvider,
        # "google": GoogleProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]) -> None:
        """
        Register a new LLM provider.

        Args:
            name: Provider name (e.g., 'openai', 'anthropic')
            provider_class: Provider class that implements BaseLLMProvider
        """
        cls._providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")

    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> BaseLLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_name: Name of the provider to create
            **kwargs: Provider-specific configuration

        Returns:
            Initialized LLM provider instance

        Raises:
            LLMError: If provider not found or initialization fails
        """
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise LLMError(
                f"Unknown LLM provider '{provider_name}'. Available providers: {available}"
            )

        provider_class = cls._providers[provider_name]
        try:
            logger.info(f"Creating LLM provider: {provider_name}")
            return provider_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create LLM provider '{provider_name}': {e}")
            raise LLMError(f"Failed to create provider '{provider_name}': {e}")

    @classmethod
    def create_from_config(cls, config: Any) -> BaseLLMProvider:
        """
        Create an LLM provider from configuration object.

        Args:
            config: LLMConfig object with provider settings

        Returns:
            Initialized LLM provider instance
        """
        provider_kwargs = {
            "api_key": config.api_key,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        # Add provider-specific configs
        if config.provider == "azure_openai" and config.azure_openai:
            provider_kwargs.update({
                "endpoint": config.azure_openai.endpoint,
                "deployment": config.azure_openai.deployment,
                "api_version": config.azure_openai.api_version,
            })

        return cls.create(config.provider, **provider_kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered providers.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
