"""Configuration schema using Pydantic models."""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class GitProvider(str, Enum):
    """Supported Git providers."""
    AZURE_DEVOPS = "azure_devops"
    GITHUB = "github"
    GITLAB = "gitlab"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"


class UIFramework(str, Enum):
    """Supported UI frameworks."""
    STREAMLIT = "streamlit"
    GRADIO = "gradio"


class GitConfig(BaseModel):
    """Git configuration."""
    provider: GitProvider = GitProvider.AZURE_DEVOPS
    organization_url: str = Field(..., description="Azure DevOps organization URL")
    project: str = Field(..., description="Project name")
    token: str = Field(..., description="Personal Access Token")
    base_branch: str = Field(default="main", description="Base branch name")
    branch_prefix: str = Field(default="coverage-improvement", description="Branch prefix for PRs")


class SonarQubeConfig(BaseModel):
    """SonarQube configuration."""
    url: str = Field(..., description="SonarQube server URL")
    token: str = Field(..., description="SonarQube authentication token")
    project_key: str = Field(..., description="SonarQube project key")
    coverage_threshold: int = Field(default=90, ge=0, le=100, description="Minimum coverage threshold")
    metrics: List[str] = Field(default=["coverage", "line_coverage", "branch_coverage"])


class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI specific configuration."""
    endpoint: Optional[str] = None
    deployment: Optional[str] = None
    api_version: str = "2024-02-15-preview"


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = Field(default="gpt-4", description="Model name")
    api_key: str = Field(..., description="API key for the provider")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, gt=0)
    azure_openai: Optional[AzureOpenAIConfig] = None


class WorkflowConfig(BaseModel):
    """Workflow configuration."""
    max_retries: int = Field(default=3, ge=0)
    timeout_seconds: int = Field(default=3600, gt=0)
    parallel_test_generation: bool = False
    max_tests_per_file: int = Field(default=10, gt=0)
    prioritize_by_complexity: bool = True


class CodeAnalysisConfig(BaseModel):
    """Code analysis configuration."""
    languages: List[str] = Field(default=["python"])
    exclude_patterns: List[str] = Field(
        default=[
            "*/tests/*",
            "*/test_*",
            "*/__pycache__/*",
            "*/venv/*",
            "*/node_modules/*",
        ]
    )
    min_function_lines: int = Field(default=3, ge=1)


class TestGenerationConfig(BaseModel):
    """Test generation configuration."""
    framework: str = Field(default="pytest")
    include_fixtures: bool = True
    include_mocks: bool = True
    test_file_pattern: str = "test_{module}.py"
    test_directory: str = "tests"


class APIConfig(BaseModel):
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = Field(default=8000, gt=0, lt=65536)
    cors_origins: List[str] = Field(default=["*"])
    enable_docs: bool = True
    max_concurrent_workflows: int = Field(default=5, gt=0)


class UIConfig(BaseModel):
    """UI configuration."""
    framework: UIFramework = UIFramework.STREAMLIT
    port: int = Field(default=8501, gt=0, lt=65536)
    theme: str = "dark"
    title: str = "Code Coverage Agent"
    description: str = "Automated code coverage improvement system"


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/agent.log"
    max_bytes: int = Field(default=10485760)  # 10MB
    backup_count: int = Field(default=5, ge=0)

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()


class Settings(BaseModel):
    """Main settings configuration."""
    git: GitConfig
    sonarqube: SonarQubeConfig
    llm: LLMConfig
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    code_analysis: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)
    test_generation: TestGenerationConfig = Field(default_factory=TestGenerationConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        """Pydantic config."""
        use_enum_values = True
