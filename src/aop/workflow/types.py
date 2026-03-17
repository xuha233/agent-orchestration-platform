"""Workflow-native types for the unified AOP runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


class WorkflowPhase(Enum):
    """Canonical internal workflow phases."""

    CLARIFY = "clarify"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    GAP_CLOSE = "gap_close"
    LEARN = "learn"
    COMPLETE = "complete"


@dataclass
class WorkflowTask:
    """A planned unit of work for a workflow run."""

    task_id: str
    title: str
    description: str = ""
    hypothesis_id: str = ""
    dependencies: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    objective: str = ""
    output_format: str = ""
    tools_guidance: str = ""
    boundaries: str = ""
    effort_budget: int = 10


@dataclass
class WorkflowPlan:
    """Persisted planning artifact for a workflow run."""

    summary: str
    goals: List[str] = field(default_factory=list)
    tasks: List[WorkflowTask] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass
class VerificationCheck:
    """A single verification checkpoint."""

    name: str
    status: str
    details: str = ""


@dataclass
class VerificationReport:
    """Persisted verification artifact for a workflow run."""

    summary: str
    verdict: str
    truths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    checks: List[VerificationCheck] = field(default_factory=list)


@dataclass
class GapItem:
    """A concrete gap discovered during verification."""

    gap_id: str
    title: str
    description: str = ""
    source: str = ""
    severity: str = "important"
    suggested_action: str = ""
    verification_target: str = ""


@dataclass
class GapClosurePlan:
    """A bounded repair plan derived from verification gaps."""

    summary: str
    gaps: List[GapItem] = field(default_factory=list)
    repair_tasks: List[WorkflowTask] = field(default_factory=list)
    stop_conditions: List[str] = field(default_factory=list)
    next_verification_steps: List[str] = field(default_factory=list)


@dataclass
class WorkflowRun:
    """Top-level workflow run metadata."""

    run_id: str
    original_input: str
    current_phase: WorkflowPhase = WorkflowPhase.CLARIFY
    status: str = "running"
    clarified_summary: str = ""
    success_criteria: List[str] = field(default_factory=list)
    hypothesis_ids: List[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
