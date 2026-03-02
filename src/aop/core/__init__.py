"""AOP core module."""

from .types import (
    ErrorKind,
    WarningKind,
    ProviderId,
    CapabilityTier,
    TaskAttemptState,
    CapabilitySet,
    ProviderPresence,
    TaskInput,
    TaskRunRef,
    TaskStatus,
    NormalizeContext,
    Evidence,
    NormalizedFinding,
    ProviderAdapter,
    TaskState,
    TaskResult,
    AttemptResult,
    RunResult,
)
from .retry import RetryPolicy
from .artifacts import expected_paths, task_artifact_root
from .adapter import (
    ShimAdapterBase,
    ClaudeAdapter,
    CodexAdapter,
    GeminiAdapter,
    OpenCodeAdapter,
    QwenAdapter,
    get_adapter_registry,
    get_available_providers,
)
from .engine import ExecutionEngine, ReviewEngine, ReviewPolicy, ReviewResult
from .orchestrator import OrchestratorRuntime, TaskStateMachine


__all__ = [
    # Types
    "ErrorKind",
    "WarningKind",
    "ProviderId",
    "CapabilityTier",
    "TaskAttemptState",
    "CapabilitySet",
    "ProviderPresence",
    "TaskInput",
    "TaskRunRef",
    "TaskStatus",
    "NormalizeContext",
    "Evidence",
    "NormalizedFinding",
    "ProviderAdapter",
    "TaskState",
    "TaskResult",
    "AttemptResult",
    "RunResult",
    # Retry
    "RetryPolicy",
    # Artifacts
    "expected_paths",
    "task_artifact_root",
    # Adapter
    "ShimAdapterBase",
    "ClaudeAdapter",
    "CodexAdapter",
    "GeminiAdapter",
    "OpenCodeAdapter",
    "QwenAdapter",
    "get_adapter_registry",
    "get_available_providers",
    # Engine
    "ExecutionEngine",
    "ReviewEngine",
    "ReviewPolicy",
    "ReviewResult",
    # Orchestrator
    "OrchestratorRuntime",
    "TaskStateMachine",
]
