"""Error classification for provider adapters."""

from __future__ import annotations

import re
from typing import List

from ..types.errors import ErrorKind, WarningKind


def detect_warnings(stderr: str) -> List[WarningKind]:
    """Detect warnings from provider stderr output."""
    text = stderr.lower()
    warnings: List[WarningKind] = []
    if "mcp" in text and ("failed to start" in text or "auth required" in text):
        warnings.append(WarningKind.PROVIDER_WARNING_MCP_STARTUP)
    return warnings


def classify_error(exit_code: int, stderr: str) -> ErrorKind:
    """Classify an error based on exit code and stderr output.
    
    Args:
        exit_code: The process exit code
        stderr: The stderr output from the process
    
    Returns:
        An ErrorKind classification
    """
    text = stderr.lower()

    # Timeout errors
    if exit_code in (124, 142) or "timeout" in text or "timed out" in text:
        return ErrorKind.RETRYABLE_TIMEOUT

    # Rate limiting
    if "rate limit" in text or "429" in text:
        return ErrorKind.RETRYABLE_RATE_LIMIT

    # Network errors
    if any(token in text for token in ("connection reset", "temporary failure", "network", "econnreset", "ehostunreach")):
        return ErrorKind.RETRYABLE_TRANSIENT_NETWORK

    # Authentication errors
    if any(token in text for token in ("auth", "invalid api key", "401", "oauth", "unauthorized")):
        return ErrorKind.NON_RETRYABLE_AUTH

    # Capability errors
    if any(token in text for token in ("unsupported capability", "not supported", "unknown arguments")):
        return ErrorKind.NON_RETRYABLE_UNSUPPORTED_CAPABILITY

    # Input validation errors
    if any(token in text for token in ("invalid input", "schema", "missing required", "validation failed", "invalid type")):
        return ErrorKind.NON_RETRYABLE_INVALID_INPUT

    # Parsing/normalization errors
    if re.search(r"(parse|deserialize|json).*fail", text) or "normalization" in text:
        return ErrorKind.NORMALIZATION_ERROR

    return ErrorKind.NORMALIZATION_ERROR
