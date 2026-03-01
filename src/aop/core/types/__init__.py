"""Core type definitions for AOP."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Literal, Optional


ProviderId = Literal["claude", "codex", "gemini", "opencode", "qwen"]


class TaskState(str, Enum):
    """Task execution state."""
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HypothesisState(str, Enum):
    """Hypothesis validation state."""
    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    FALSIFIED = "falsified"


class ProjectType(str, Enum):
    """Project classification based on complexity assessment."""
    EXPLORATORY = "exploratory"
    OPTIMIZATION = "optimization"
    TRANSFORMATION = "transformation"
    COMPLIANCE_SENSITIVE = "compliance_sensitive"


@dataclass(frozen=True)
class Evidence:
    """Evidence for a finding (file location and snippet)."""
    file: str
    line: Optional[int] = None
    snippet: str = ""


@dataclass(frozen=True)
class NormalizedFinding:
    """Normalized finding from any provider."""
    finding_id: str
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal["bug", "security", "performance", "maintainability"]
    title: str
    evidence: Evidence
    recommendation: str
    detected_by: List[ProviderId] = field(default_factory=list)


@dataclass
class TaskInput:
    """Input for a task to be executed by a provider."""
    task_id: str
    prompt: str
    repo_root: str = "."
    timeout_seconds: int = 600


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    provider: ProviderId
    success: bool
    output: Optional[str] = None
    findings: List[NormalizedFinding] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class Hypothesis:
    """A hypothesis to be validated."""
    hypothesis_id: str
    statement: str
    validation_method: str = ""
    success_criteria: List[str] = field(default_factory=list)
    state: HypothesisState = HypothesisState.PENDING
    priority: str = "quick_win"
    findings: List[NormalizedFinding] = field(default_factory=list)


@dataclass
class LearningCapture:
    """Captured learnings from a phase or iteration."""
    phase: str
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)


@dataclass
class ComplexityAssessment:
    """Assessment of project complexity."""
    problem_clarity: str = "medium"
    data_availability: str = "medium"
    tech_novelty: str = "medium"
    business_risk: str = "medium"
    
    def to_project_type(self) -> "ProjectType":
        """Determine project type based on complexity assessment."""
        if self.tech_novelty == "high" and self.data_availability == "low":
            return ProjectType.EXPLORATORY
        elif self.business_risk == "high":
            return ProjectType.COMPLIANCE_SENSITIVE
        elif self.problem_clarity == "high":
            return ProjectType.OPTIMIZATION
        return ProjectType.TRANSFORMATION


@dataclass
class TeamConfig:
    """Team configuration based on project type."""
    project_type: ProjectType
    agents: List[str] = field(default_factory=list)
    iteration_length: str = "2 weeks"
    priority: str = "balanced"
    
    @classmethod
    def from_project_type(cls, pt: "ProjectType") -> "TeamConfig":
        """Create team config based on project type."""
        configs = {
            ProjectType.EXPLORATORY: ["product_owner", "data", "ml"],
            ProjectType.OPTIMIZATION: ["product_owner", "data", "ml", "dev", "devops"],
            ProjectType.TRANSFORMATION: ["product_owner", "data", "ml", "dev", "ux", "devops"],
            ProjectType.COMPLIANCE_SENSITIVE: ["product_owner", "data", "ml", "dev", "ux", "devops", "ethics"],
        }
        return cls(project_type=pt, agents=configs.get(pt, []))
