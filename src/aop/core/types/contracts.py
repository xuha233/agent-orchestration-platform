"""Contract types for AOP provider adapters.

This module defines the core contracts that providers must implement,
including task input/output types, capability sets, and normalization types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence, runtime_checkable

from .errors import ErrorKind


ProviderId = Literal["claude", "codex", "gemini", "opencode", "qwen"]
CapabilityTier = Literal["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
TaskAttemptState = Literal["PENDING", "STARTED", "SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"]

PROVIDER_IDS: Sequence[ProviderId] = ("claude", "codex", "gemini", "opencode", "qwen")
CAPABILITY_TIERS: Sequence[CapabilityTier] = ("C0", "C1", "C2", "C3", "C4", "C5", "C6")


@dataclass(frozen=True)
class CapabilitySet:
    """Describes the capabilities of a provider."""
    tiers: List[CapabilityTier]
    supports_native_async: bool
    supports_poll_endpoint: bool
    supports_resume_after_restart: bool
    supports_schema_enforcement: bool
    min_supported_version: str
    tested_os: List[Literal["macos", "linux", "windows"]]


@dataclass(frozen=True)
class ProviderPresence:
    """Information about a provider's presence on the system."""
    provider: ProviderId
    detected: bool
    binary_path: Optional[str]
    version: Optional[str]
    auth_ok: bool
    reason: str = ""


@dataclass(frozen=True)
class TaskInput:
    """Input for a task to be executed by a provider."""
    task_id: str
    prompt: str
    repo_root: str
    target_paths: List[str]
    required_capabilities: List[CapabilityTier] = field(default_factory=lambda: ["C1", "C2"])
    optional_capabilities: List[CapabilityTier] = field(default_factory=list)
    timeout_seconds: int = 600
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskRunRef:
    """Reference to a running task."""
    task_id: str
    provider: ProviderId
    run_id: str
    artifact_path: str
    started_at: str
    pid: Optional[int] = None
    session_id: Optional[str] = None


@dataclass(frozen=True)
class TaskStatus:
    """Status of a task execution."""
    task_id: str
    provider: ProviderId
    run_id: str
    attempt_state: TaskAttemptState
    completed: bool
    heartbeat_at: Optional[str]
    output_path: Optional[str]
    error_kind: Optional[ErrorKind] = None
    exit_code: Optional[int] = None
    message: str = ""


@dataclass(frozen=True)
class NormalizeContext:
    """Context for normalizing provider output."""
    task_id: str
    provider: ProviderId
    repo_root: str
    raw_ref: str


@dataclass(frozen=True)
class Evidence:
    """Evidence for a finding (file location and snippet)."""
    file: str
    line: Optional[int]
    snippet: str
    symbol: Optional[str] = None


@dataclass(frozen=True)
class NormalizedFinding:
    """Normalized finding from any provider."""
    task_id: str
    provider: ProviderId
    finding_id: str
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal["bug", "security", "performance", "maintainability", "test-gap"]
    title: str
    evidence: Evidence
    recommendation: str
    confidence: float
    fingerprint: str
    raw_ref: str


@runtime_checkable
class ProviderAdapter(Protocol):
    """Protocol that all provider adapters must implement."""
    id: ProviderId

    def detect(self) -> ProviderPresence:
        """Detect if the provider is installed and available."""
        ...

    def capabilities(self) -> CapabilitySet:
        """Get the capabilities of this provider."""
        ...

    def run(self, input_task: TaskInput) -> TaskRunRef:
        """Start running a task."""
        ...

    def poll(self, ref: TaskRunRef) -> TaskStatus:
        """Poll the status of a running task."""
        ...

    def cancel(self, ref: TaskRunRef) -> None:
        """Cancel a running task."""
        ...

    def normalize(self, raw: Any, ctx: NormalizeContext) -> List[NormalizedFinding]:
        """Normalize provider output into findings."""
        ...
