"""Error classification for AOP."""

from __future__ import annotations

from enum import Enum


class ErrorKind(str, Enum):
    """Classification of errors that can occur during task execution."""
    RETRYABLE_TIMEOUT = "retryable_timeout"
    RETRYABLE_RATE_LIMIT = "retryable_rate_limit"
    RETRYABLE_TRANSIENT_NETWORK = "retryable_transient_network"
    NON_RETRYABLE_AUTH = "non_retryable_auth"
    NON_RETRYABLE_INVALID_INPUT = "non_retryable_invalid_input"
    NON_RETRYABLE_UNSUPPORTED_CAPABILITY = "non_retryable_unsupported_capability"
    NORMALIZATION_ERROR = "normalization_error"


class WarningKind(str, Enum):
    """Classification of warnings that can occur during task execution."""
    PROVIDER_WARNING_MCP_STARTUP = "provider_warning_mcp_startup"
