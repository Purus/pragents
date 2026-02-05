"""OpenAI LLM provider implementation."""
import json
from typing import Any, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from ..base import BaseLLMProvider, LLMResponse, LLMError, LLMAuthenticationError
from ...utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, **kwargs: Any):
        """
        Initialize OpenAI provider.

        Required kwargs:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            temperature: Temperature for generation (default: 0.2)
            max_tokens: Maximum tokens to generate (default: 4000)
        """
        super().__init__(**kwargs)
        self._validate_config(["api_key", "model"])

        try:
            self.client = ChatOpenAI(
                api_key=self.config["api_key"],
                model=self.config["model"],
                temperature=self.config.get("temperature", 0.2),
                max_tokens=self.config.get("max_tokens", 4000),
            )
            logger.info(f"Initialized OpenAI provider with model: {self.config['model']}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")
            raise LLMAuthenticationError(f"OpenAI initialization failed: {e}")

    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Generate text using OpenAI.

        Args:
            prompt: The input prompt
            system_message: Optional system message
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated content
        """
        try:
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))

            logger.debug(f"Generating with OpenAI, prompt length: {len(prompt)}")
            response = self.client.invoke(messages, **kwargs)

            return LLMResponse(
                content=response.content,
                model=self.config["model"],
                usage={
                    "prompt_tokens": response.response_metadata.get("token_usage", {}).get("prompt_tokens"),
                    "completion_tokens": response.response_metadata.get("token_usage", {}).get("completion_tokens"),
                    "total_tokens": response.response_metadata.get("token_usage", {}).get("total_tokens"),
                },
                metadata=response.response_metadata,
            )
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise LLMError(f"Generation failed: {e}")

    def generate_with_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_message: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate structured output using OpenAI function calling.

        Args:
            prompt: The input prompt
            schema: JSON schema for expected output
            system_message: Optional system message
            **kwargs: Additional parameters

        Returns:
            Dictionary matching the schema
        """
        try:
            # Use function calling for structured output
            function_spec = {
                "name": "generate_output",
                "description": "Generate structured output",
                "parameters": schema
            }

            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))

            logger.debug(f"Generating structured output with schema: {schema.get('title', 'unnamed')}")
            
            # Bind the function to the model
            model_with_function = self.client.bind(
                functions=[function_spec],
                function_call={"name": "generate_output"}
            )
            
            response = model_with_function.invoke(messages, **kwargs)
            
            # Extract function call arguments
            if hasattr(response, "additional_kwargs") and "function_call" in response.additional_kwargs:
                function_call = response.additional_kwargs["function_call"]
                result = json.loads(function_call["arguments"])
                return result
            else:
                # Fallback: try to parse JSON from content
                try:
                    return json.loads(response.content)
                except json.JSONDecodeError:
                    raise LLMError("Failed to extract structured output from response")

        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            raise LLMError(f"Structured generation failed: {e}")
