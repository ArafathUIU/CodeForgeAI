"""Configuration loader for CodeForge.

Loads settings from environment variables with sensible defaults.
Uses .env file via python-dotenv for local development.
"""

import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

from codeforge.utils.exceptions import ConfigurationError

_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        _ENV_LOADED = True
        load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    _ensure_env_loaded()
    return os.getenv(key, default)


def _get_env_int(key: str, default: int) -> int:
    value = _get_env(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_float(key: str, default: float) -> float:
    value = _get_env(key, str(default))
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    value = _get_env(key, str(default)).lower()
    true_values = ("true", "1", "yes", "on")
    false_values = ("false", "0", "no", "off")
    if value in true_values:
        return True
    if value in false_values:
        return False
    return default


@dataclass
class LLMConfig:
    host: str = field(default_factory=lambda: _get_env("OLLAMA_HOST", "http://localhost:11434"))
    model: str = field(default_factory=lambda: _get_env("OLLAMA_MODEL", "llama3.2"))
    temperature: float = field(default_factory=lambda: _get_env_float("OLLAMA_TEMPERATURE", 0.2))
    max_tokens: int = field(default_factory=lambda: _get_env_int("OLLAMA_MAX_TOKENS", 4096))
    timeout: int = field(default_factory=lambda: _get_env_int("OLLAMA_TIMEOUT", 120))

    @property
    def api_url(self) -> str:
        return f"{self.host}/api"


@dataclass
class AgentConfig:
    timeout_seconds: int = field(
        default_factory=lambda: _get_env_int("AGENT_TIMEOUT_SECONDS", 300)
    )
    max_retry_attempts: int = field(
        default_factory=lambda: _get_env_int("MAX_RETRY_ATTEMPTS", 3)
    )
    retry_delay_seconds: int = field(
        default_factory=lambda: _get_env_int("RETRY_DELAY_SECONDS", 5)
    )


@dataclass
class StorageConfig:
    state_store_path: str = field(
        default_factory=lambda: _get_env("STATE_STORE_PATH", ".codeforge/state")
    )
    checkpoint_path: str = field(
        default_factory=lambda: _get_env("CHECKPOINT_PATH", ".codeforge/checkpoints")
    )


@dataclass
class GitConfig:
    author_name: str = field(
        default_factory=lambda: _get_env("GIT_AUTHOR_NAME", "CodeForge AI")
    )
    author_email: str = field(
        default_factory=lambda: _get_env("GIT_AUTHOR_EMAIL", "codeforge@ai.local")
    )


@dataclass
class DashboardConfig:
    host: str = field(default_factory=lambda: _get_env("DASHBOARD_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _get_env_int("DASHBOARD_PORT", 8501))


@dataclass
class ApprovalConfig:
    auto_approve_style_fixes: bool = field(
        default_factory=lambda: _get_env_bool("AUTO_APPROVE_STYLE_FIXES", True)
    )
    approval_timeout_minutes: int = field(
        default_factory=lambda: _get_env_int("APPROVAL_TIMEOUT_MINUTES", 30)
    )


@dataclass
class LoggingConfig:
    level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "INFO"))
    format: str = field(default_factory=lambda: _get_env("LOG_FORMAT", "json"))


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    git: GitConfig = field(default_factory=GitConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance from environment variables."""
        _ensure_env_loaded()
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create a Config instance from a dictionary (useful for testing)."""
        config = cls()
        if "llm" in data:
            for key, value in data["llm"].items():
                setattr(config.llm, key, value)
        if "agent" in data:
            for key, value in data["agent"].items():
                setattr(config.agent, key, value)
        if "storage" in data:
            for key, value in data["storage"].items():
                setattr(config.storage, key, value)
        if "git" in data:
            for key, value in data["git"].items():
                setattr(config.git, key, value)
        if "dashboard" in data:
            for key, value in data["dashboard"].items():
                setattr(config.dashboard, key, value)
        if "approval" in data:
            for key, value in data["approval"].items():
                setattr(config.approval, key, value)
        if "logging" in data:
            for key, value in data["logging"].items():
                setattr(config.logging, key, value)
        return config

    def validate(self) -> None:
        """Validate configuration and raise ConfigurationError if invalid."""
        if not self.llm.host:
            raise ConfigurationError(
                "OLLAMA_HOST is not set",
                code="MISSING_LLM_HOST",
            )
        if not self.llm.model:
            raise ConfigurationError(
                "OLLAMA_MODEL is not set",
                code="MISSING_LLM_MODEL",
            )
        if self.llm.temperature < 0 or self.llm.temperature > 2:
            raise ConfigurationError(
                f"OLLAMA_TEMPERATURE must be between 0 and 2, got {self.llm.temperature}",
                code="INVALID_TEMPERATURE",
            )
        if self.agent.timeout_seconds < 1:
            raise ConfigurationError(
                "AGENT_TIMEOUT_SECONDS must be positive",
                code="INVALID_TIMEOUT",
            )


_config_instance: Config | None = None


def get_config() -> Config:
    """Get the global Config instance, creating it if necessary."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.from_env()
    return _config_instance


def set_config(config: Config) -> None:
    """Override the global Config instance (useful for testing)."""
    global _config_instance
    _config_instance = config


def reset_config() -> None:
    """Reset the global Config instance."""
    global _config_instance
    _config_instance = None
