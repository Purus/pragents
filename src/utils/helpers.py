"""Helper utilities and common functions."""
import functools
import time
from pathlib import Path
from typing import Any, Callable, TypeVar, Optional
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


def ensure_directory(path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists
    """
    path.mkdir(parents=True, exist_ok=True)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Retry decorator for functions that may fail transiently.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exponential_backoff: If True, double delay after each retry
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)

                    if exponential_backoff:
                        current_delay *= 2

            # This should never be reached, but satisfies type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper
    return decorator


def sanitize_branch_name(name: str) -> str:
    """
    Sanitize a string to be used as a git branch name.

    Args:
        name: Input string to sanitize

    Returns:
        Sanitized branch name
    """
    # Replace spaces and special characters with hyphens
    sanitized = name.lower().strip()
    sanitized = "".join(c if c.isalnum() or c in "-_" else "-" for c in sanitized)
    # Remove multiple consecutive hyphens
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")
    return sanitized


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix
