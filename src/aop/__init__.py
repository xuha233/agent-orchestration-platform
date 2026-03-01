"""AOP - Agent Orchestration Platform."""

__version__ = "0.1.0"

from .core.types import (
    ComplexityAssessment,
    Evidence,
    Hypothesis,
    HypothesisState,
    LearningCapture,
    NormalizedFinding,
    ProjectType,
    TaskInput,
    TaskResult,
    TaskState,
    TeamConfig,
)
from .core.engine import ExecutionEngine
from .workflow.hypothesis import HypothesisManager
from .workflow.learning import LearningLog
from .workflow.team import TeamOrchestrator
from .config import AOPConfig, load_config
from .report import ReportGenerator
