"""Custom exception hierarchy for CodeForge."""


class CodeForgeError(Exception):
    """Base exception for all CodeForge errors."""

    def __init__(self, message: str, *, code: str = "UNKNOWN", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AgentError(CodeForgeError):
    """Base exception for agent-related errors."""
    pass


class AgentTimeoutError(AgentError):
    """Raised when an agent exceeds its allowed execution time."""
    pass


class AgentTaskFailureError(AgentError):
    """Raised when an agent fails to complete its assigned task."""
    pass


class AgentNotFoundError(AgentError):
    """Raised when a requested agent is not registered."""
    pass


class MessageProtocolError(CodeForgeError):
    """Base exception for message protocol violations."""
    pass


class InvalidMessageError(MessageProtocolError):
    """Raised when a message fails schema validation."""
    pass


class MessageDeliveryError(MessageProtocolError):
    """Raised when a message cannot be delivered."""
    pass


class ConfigurationError(CodeForgeError):
    """Raised for invalid configuration."""
    pass


class StateStoreError(CodeForgeError):
    """Base exception for state store errors."""
    pass


class StateNotFoundError(StateStoreError):
    """Raised when requested state does not exist."""
    pass


class CheckpointError(CodeForgeError):
    """Base exception for checkpoint system errors."""
    pass


class RollbackError(CheckpointError):
    """Raised when a rollback operation fails."""
    pass


class ConflictResolutionError(CodeForgeError):
    """Base exception for conflict resolution errors."""
    pass


class UnresolvableConflictError(ConflictResolutionError):
    """Raised when a conflict cannot be automatically resolved."""
    pass


class PipelineError(CodeForgeError):
    """Base exception for pipeline execution errors."""
    pass


class PhaseTransitionError(PipelineError):
    """Raised when an invalid phase transition is attempted."""
    pass


class ArtifactError(CodeForgeError):
    """Base exception for artifact validation errors."""
    pass


class ArtifactValidationError(ArtifactError):
    """Raised when an artifact fails validation."""
    pass


class GitIntegrationError(CodeForgeError):
    """Base exception for Git integration errors."""
    pass


class LLMClientError(CodeForgeError):
    """Base exception for LLM client errors."""
    pass


class LLMConnectionError(LLMClientError):
    """Raised when the LLM server is unreachable."""
    pass


class LLMResponseError(LLMClientError):
    """Raised when an LLM response is invalid or unparseable."""
    pass
