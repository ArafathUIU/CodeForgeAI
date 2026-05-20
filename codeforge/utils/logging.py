"""Structured logging setup for CodeForge.

Provides JSON and console log formatters with agent and phase context.
"""

import logging
import sys
from datetime import UTC, datetime
from typing import Any

from codeforge.utils.config import LoggingConfig


class JsonFormatter(logging.Formatter):
    """Formats log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "agent_id"):
            log_entry["agent_id"] = record.agent_id
        if hasattr(record, "phase"):
            log_entry["phase"] = record.phase
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
                "agent_id", "phase", "correlation_id",
            } and key not in log_entry:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter with colors via ANSI codes."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"
    DIM = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")
        level = f"{color}{record.levelname:<8}{self.RESET}"
        name = f"{self.DIM}{record.name}{self.RESET}"

        parts = [f"{self.DIM}{timestamp}{self.RESET} {level} {name}"]

        if hasattr(record, "agent_id"):
            parts.append(f"[{record.agent_id}]")
        if hasattr(record, "phase"):
            parts.append(f"[phase:{record.phase}]")

        parts.append(record.getMessage())

        if record.exc_info and record.exc_info[1]:
            parts.append(f"\n{color}{record.exc_info[1]}{self.RESET}")

        return " ".join(parts)


class AgentLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that injects agent context into log records."""

    def __init__(self, logger: logging.Logger, agent_id: str = "", phase: str = ""):
        super().__init__(logger, {})
        self.agent_id = agent_id
        self.phase = phase

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        extra = kwargs.get("extra", {})
        extra["agent_id"] = self.agent_id
        extra["phase"] = self.phase
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(config: LoggingConfig) -> None:
    """Configure the root logger for CodeForge."""
    root = logging.getLogger("codeforge")
    root.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    root.handlers.clear()

    if config.format == "json":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(ConsoleFormatter())

    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str = "codeforge") -> logging.Logger:
    """Get a logger instance for the given module name."""
    return logging.getLogger(name)


def get_agent_logger(agent_id: str, phase: str = "") -> AgentLoggerAdapter:
    """Get a logger with agent context injected."""
    logger = logging.getLogger(f"codeforge.agents.{agent_id}")
    return AgentLoggerAdapter(logger, agent_id=agent_id, phase=phase)
