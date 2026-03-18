"""AOP Workflow module.

This module provides workflow management utilities including:
- Hypothesis tracking and validation
- Learning capture and export
- Team orchestration
- Persistence utilities
- Workflow run types and artifact persistence
"""

from .hypothesis import HypothesisManager
from .learning import LearningLog
from .team import TeamOrchestrator
from .persistence import PersistenceManager, get_persistence_manager
from .artifacts import WorkflowArtifactManager
from .checks import (
    CompletionDecision,
    CompletionGate,
    GuardrailReport,
    PlanCheckIssue,
    PlanCheckReport,
    WorkflowLoopDetector,
    WorkflowPlanChecker,
)
from .reader import WorkflowRunReader, WorkflowRunSummary
from .runtime import WorkflowRuntime
from .types import (
    GapClosurePlan,
    GapItem,
    VerificationCheck,
    VerificationReport,
    WorkflowPhase,
    WorkflowPlan,
    WorkflowRun,
    WorkflowTask,
)

__all__ = [
    "HypothesisManager",
    "LearningLog",
    "TeamOrchestrator",
    "PersistenceManager",
    "get_persistence_manager",
    "WorkflowArtifactManager",
    "WorkflowRunReader",
    "WorkflowRunSummary",
    "WorkflowRuntime",
    "WorkflowPlanChecker",
    "PlanCheckIssue",
    "PlanCheckReport",
    "CompletionGate",
    "CompletionDecision",
    "WorkflowLoopDetector",
    "GuardrailReport",
    "GapItem",
    "GapClosurePlan",
    "WorkflowPhase",
    "WorkflowRun",
    "WorkflowPlan",
    "WorkflowTask",
    "VerificationReport",
    "VerificationCheck",
]
