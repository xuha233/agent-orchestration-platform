"""
Agent 自动化模块

从模糊需求到交付的全自动 Agent 团队驱动。
支持双模式：
- OrchestratorClient 模式：使用中枢 Agent 进行决策和调度
- LLMClient 模式：直接调用 LLM API（向后兼容）
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
    # Orchestrator 相关（新增）
    "OrchestratorClient",
    "OrchestratorConfig",
    "OrchestratorMode",
    "OrchestratorCapability",
    "create_orchestrator",
    "get_best_orchestrator",
    "get_available_orchestrators",
]
