"""Settings loader and configuration management."""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from .schema import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def substitute_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively substitute environment variables in configuration values.

    Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with environment variables substituted
    """
    if isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Handle ${VAR_NAME} or ${VAR_NAME:default}
        if config.startswith("${") and config.endswith("}"):
            var_spec = config[2:-1]
            if ":" in var_spec:
                var_name, default_value = var_spec.split(":", 1)
                return os.getenv(var_name, default_value)
            else:
                var_name = var_spec
                value = os.getenv(var_name)
                if value is None:
                    raise ConfigurationError(
                        f"Environment variable {var_name} is required but not set"
                    )
                return value
        return config
    else:
        return config


def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Configuration dictionary

    Raises:
        ConfigurationError: If file not found or invalid YAML
    """
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config if config else {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")


def load_settings(
    config_path: Optional[Path] = None,
    env_file: Optional[Path] = None,
) -> Settings:
    """
    Load and validate settings from configuration file and environment.

    Args:
        config_path: Path to YAML configuration file (default: config/default.yaml)
        env_file: Path to .env file (default: .env)

    Returns:
        Validated Settings object

    Raises:
        ConfigurationError: If configuration is invalid
    """
    # Load environment variables
    if env_file is None:
        env_file = Path(".env")
    
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
    else:
        logger.warning(f"Environment file not found: {env_file}")

    # Load YAML configuration
    if config_path is None:
        config_path = Path("config/default.yaml")

    logger.info(f"Loading configuration from {config_path}")
    config_dict = load_yaml_config(config_path)

    # Substitute environment variables
    config_dict = substitute_env_vars(config_dict)

    # Validate and create Settings object
    try:
        settings = Settings(**config_dict)
        logger.info("Configuration loaded and validated successfully")
        return settings
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ConfigurationError(f"Invalid configuration: {e}")


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings(
    config_path: Optional[Path] = None,
    env_file: Optional[Path] = None,
    reload: bool = False,
) -> Settings:
    """
    Get the global settings instance.

    Args:
        config_path: Path to YAML configuration file
        env_file: Path to .env file
        reload: Force reload of settings

    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None or reload:
        _settings = load_settings(config_path, env_file)
    
    return _settings
