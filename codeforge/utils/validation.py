"""Input validation utilities for CodeForge.

Provides reusable validators for messages, artifacts, and configuration.
"""

import re
from typing import Any, Callable
from uuid import UUID


class Validator:
    """Composable validation framework."""

    def __init__(self, name: str, validate_fn: Callable[[Any], bool], message: str = ""):
        self.name = name
        self._validate = validate_fn
        self.message = message or f"Validation failed: {name}"

    def __call__(self, value: Any) -> bool:
        return self._validate(value)

    def check(self, value: Any) -> None:
        """Validate and raise ValueError on failure."""
        if not self(value):
            raise ValueError(self.message)


class ValidationResult:
    """Result of running multiple validators."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def raise_if_invalid(self) -> None:
        if not self.is_valid:
            raise ValueError("; ".join(self.errors))

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        return (
            f"ValidationResult(valid={self.is_valid}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)})"
        )


is_non_empty_string = Validator(
    "non_empty_string",
    lambda v: isinstance(v, str) and len(v.strip()) > 0,
    "Value must be a non-empty string",
)

is_valid_uuid = Validator(
    "valid_uuid",
    lambda v: _try_parse_uuid(v),
    "Value must be a valid UUID",
)

is_positive_int = Validator(
    "positive_int",
    lambda v: isinstance(v, int) and v > 0,
    "Value must be a positive integer",
)

is_non_negative_int = Validator(
    "non_negative_int",
    lambda v: isinstance(v, int) and v >= 0,
    "Value must be a non-negative integer",
)

is_valid_url = Validator(
    "valid_url",
    lambda v: isinstance(v, str) and _is_url(v),
    "Value must be a valid URL",
)

is_valid_agent_id = Validator(
    "valid_agent_id",
    lambda v: isinstance(v, str) and re.match(r"^[a-z][a-z0-9_]{1,31}$", v) is not None,
    "Agent ID must be lowercase, start with a letter, and be 2-32 chars",
)

is_valid_phase = Validator(
    "valid_phase",
    lambda v: v in {
        "requirements", "architecture", "implementation",
        "testing", "review", "deployment", "complete",
    },
    "Phase must be one of the supported CodeForge pipeline phases",
)


def _try_parse_uuid(value: Any) -> bool:
    try:
        if isinstance(value, UUID):
            return True
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _is_url(value: str) -> bool:
    pattern = re.compile(
        r"^https?://"
        r"[\w\-]+(\.[\w\-]+)*"
        r"(:\d+)?"
        r"(/[\w\-./?%&=]*)?$"
    )
    return bool(pattern.match(value))
