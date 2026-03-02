"""Retry policy for AOP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Policy for retrying failed operations."""
    max_retries: int = 2
    base_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0

    def compute_delay(self, retry_index: int) -> float:
        """Compute the delay for a given retry attempt.
        
        Args:
            retry_index: The retry index (1 for first retry, 2 for second, etc.)
        
        Returns:
            The delay in seconds.
        """
        return self.base_delay_seconds * (self.backoff_multiplier ** (retry_index - 1))
