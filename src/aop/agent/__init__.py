"""
Agent 自动化模块

从模糊需求到交付的全自动 Agent 团队驱动。
支持双模式：
- OrchestratorClient 模式：使用中枢 Agent 进行决策和调度
- LLMClient 模式：直接调用 LLM API（向后兼容）

Phase 1-5 改进（基于 Anthropic 多智能体研究）：
- Phase 1: 标准化 Prompt 模块
- Phase 2: 任务前验证系统
- Phase 3: 动态超时管理
- Phase 4: LLM-as-Judge 评估器
- Phase 5: 错误恢复机制
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

# Phase 1: Prompts
from .prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
    HYPOTHESIS_GENERATION_SYSTEM_PROMPT,
    SUBAGENT_TASK_TEMPLATE,
    VALIDATION_SYSTEM_PROMPT,
    LEARNING_EXTRACTION_SYSTEM_PROMPT,
    SubagentTaskInput,
    build_subagent_task,
)

# Phase 2: Pre-flight validation
from .preflight import (
    PreFlightCheck,
    PreFlightResult,
    PreFlightStatus,
    PreFlightValidator,
    run_preflight,
)

# Phase 4: LLM-as-Judge
from .llm_evaluator import (
    EvaluationVerdict,
    EvaluationScore,
    EvaluationResult,
    CodeArtifact,
    LLMEvaluator,
    HumanAICollaboration,
)

# Phase 5: Error Recovery
from .error_recovery import (
    ErrorType,
    RecoveryAction,
    RecoveryDecision,
    ErrorContext,
    RetryState,
    ErrorClassifier,
    RecoveryStrategy,
    ErrorRecoveryManager,
    CheckpointManager,
    RecoveryCompletedException,
)

# Orchestrator 相关类型重导出（方便使用）
from ..orchestrator import (
    OrchestratorClient,
    OrchestratorConfig,
    OrchestratorMode,
    OrchestratorCapability,
    create_orchestrator,
    get_best_orchestrator,
    get_available_orchestrators,
)

__all__ = [
    # Sprint 类型
    "SprintState",
    "SprintContext",
    "SprintResult",
    # 需求澄清
    "ClarifiedRequirement",
    "QAPair",
    # 假设生成
    "GeneratedHypothesis",
    "HypothesisType",
    # 验证
    "ValidationResult",
    "ValidationVerdict",
    # 学习提取
    "ExtractedLearning",
    # 配置
    "AgentDriverConfig",
    # 驱动器
    "AgentDriver",
    "SprintPersistence",
    # Phase 1: Prompts
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "CLARIFICATION_SYSTEM_PROMPT",
    "HYPOTHESIS_GENERATION_SYSTEM_PROMPT",
    "SUBAGENT_TASK_TEMPLATE",
    "VALIDATION_SYSTEM_PROMPT",
    "LEARNING_EXTRACTION_SYSTEM_PROMPT",
    "SubagentTaskInput",
    "build_subagent_task",
    # Phase 2: Pre-flight
    "PreFlightCheck",
    "PreFlightResult",
    "PreFlightStatus",
    "PreFlightValidator",
    "run_preflight",
    # Phase 4: LLM-as-Judge
    "EvaluationVerdict",
    "EvaluationScore",
    "EvaluationResult",
    "CodeArtifact",
    "LLMEvaluator",
    "HumanAICollaboration",
    # Phase 5: Error Recovery
    "ErrorType",
    "RecoveryAction",
    "RecoveryDecision",
    "ErrorContext",
    "RetryState",
    "ErrorClassifier",
    "RecoveryStrategy",
    "ErrorRecoveryManager",
    "CheckpointManager",
    "RecoveryCompletedException",
    # Orchestrator 相关
    "OrchestratorClient",
    "OrchestratorConfig",
    "OrchestratorMode",
    "OrchestratorCapability",
    "create_orchestrator",
    "get_best_orchestrator",
    "get_available_orchestrators",
]
