"""
Agent 自动化模块

从模糊需求到交付的全自动 Agent 团队驱动。
"""

from .types import (
    SprintState,
    SprintContext,
    ClarifiedRequirement,
    QAPair,
    GeneratedHypothesis,
    HypothesisType,
    ValidationResult,
    ValidationVerdict,
    ExtractedLearning,
    SprintResult,
    AgentDriverConfig,
)
from .driver import AgentDriver
from .persistence import SprintPersistence

__all__ = [
    "SprintState",
    "SprintContext",
    "ClarifiedRequirement",
    "QAPair",
    "GeneratedHypothesis",
    "HypothesisType",
    "ValidationResult",
    "ValidationVerdict",
    "ExtractedLearning",
    "SprintResult",
    "AgentDriverConfig",
    "AgentDriver",
    "SprintPersistence",
]
