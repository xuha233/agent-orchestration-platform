"""
Agent 自动化模块类型定义

定义冲刺上下文、澄清需求、验证结果等核心类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class SprintState(Enum):
    """冲刺状态"""
    INITIALIZED = "initialized"
    CLARIFIED = "clarified"
    HYPOTHESES_GENERATED = "hypotheses_generated"
    TASKS_DECOMPOSED = "tasks_decomposed"
    EXECUTED = "executed"
    VALIDATED = "validated"
    COMPLETED = "completed"
    FAILED = "failed"


class HypothesisType(Enum):
    """假设类型"""
    TECHNICAL = "technical"
    ARCHITECTURAL = "architectural"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    BUSINESS = "business"


class ValidationVerdict(Enum):
    """验证结论"""
    VALIDATED = "validated"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"
    NEEDS_MORE_INFO = "needs_more_info"


@dataclass
class QAPair:
    """问答对"""
    question: str
    answer: str
    confidence: float = 0.0  # 0-1, 自动推断时的置信度


@dataclass
class ClarifiedRequirement:
    """澄清后的需求"""
    summary: str
    user_type: str = "unknown"
    core_features: List[str] = field(default_factory=list)
    tech_constraints: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    priority_order: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    clarifications: List[QAPair] = field(default_factory=list)


@dataclass
class GeneratedHypothesis:
    """生成的假设"""
    statement: str
    hypothesis_type: HypothesisType = HypothesisType.TECHNICAL
    validation_method: str = ""
    success_criteria: List[str] = field(default_factory=list)
    priority: str = "quick_win"
    estimated_effort: str = ""
    dependencies: List[str] = field(default_factory=list)
    risk_level: str = "medium"


@dataclass
class ValidationResult:
    """验证结果"""
    hypothesis_id: str
    state: str
    verdict: ValidationVerdict
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    counter_evidence: List[str] = field(default_factory=list)
    reasoning: str = ""
    next_steps: List[str] = field(default_factory=list)


@dataclass
class ExtractedLearning:
    """提取的学习"""
    phase: str
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ExecutionTrace:
    """执行追踪记录"""
    trace_id: str
    hypothesis_id: str
    task_id: str
    provider: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "running"
    stdout: str = ""
    stderr: str = ""
    artifacts: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    error_patterns: List[str] = field(default_factory=list)
    success_patterns: List[str] = field(default_factory=list)


@dataclass
class HypothesisNode:
    """假设节点（用于依赖图）"""
    hypothesis_id: str
    statement: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    estimated_effort: str = ""
    risk_level: str = "medium"


@dataclass
class SprintContext:
    """冲刺上下文"""
    sprint_id: str
    original_input: str
    state: SprintState = SprintState.INITIALIZED
    clarified_requirement: Optional[ClarifiedRequirement] = None
    hypotheses: List[Any] = field(default_factory=list)
    task_graph: Optional[Any] = None
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    learnings: List[ExtractedLearning] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SprintResult:
    """冲刺执行结果"""
    sprint_id: str
    success: bool
    clarified_requirement: Dict[str, Any] = field(default_factory=dict)
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    learnings: List[Dict[str, Any]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class AgentDriverConfig:
    """AgentDriver 配置"""
    max_clarification_rounds: int = 3
    auto_execute: bool = True
    parallel_execution: bool = True
    auto_validate: bool = True
    auto_learn: bool = True
    storage_path: Optional[Path] = None
    progress_callback: Optional[Callable[[str, str], None]] = None
