"""
Orchestrator Layer - 中枢 Agent 抽象层

统一接口支持多种中枢类型：
- Claude Code CLI
- OpenCode CLI
- OpenClaw
- API 方式 (Claude API, OpenAI API, etc.)

使用方法：
    from aop.orchestrator import create_orchestrator, get_best_orchestrator

    # 自动选择最佳中枢
    orch_type = get_best_orchestrator()
    orchestrator = create_orchestrator(orch_type)

    # 或者指定类型
    orchestrator = create_orchestrator("claude-code")

    # 检测可用中枢
    available = get_available_orchestrators()
    
    # 多 Provider 调度
    from aop.orchestrator import MultiProviderOrchestrator, TaskType
    orchestrator = MultiProviderOrchestrator()
    results = await orchestrator.dispatch(
        prompt="Review code",
        agents=[{"name": "reviewer", "provider": "opencode"}]
    )
"""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from .types import (
    OrchestratorMode,
    OrchestratorCapability,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorConfig,
)
from .base import OrchestratorClient
from .claude_code_orchestrator import ClaudeCodeOrchestrator
from .opencode_orchestrator import OpenCodeOrchestrator
from .openclaw_orchestrator import OpenClawOrchestrator
from .api_orchestrator import APIOrchestrator
from .multi_provider_orchestrator import (
    MultiProviderOrchestrator,
    TaskType,
    ProviderStats,
    AgentSpec,
)

if TYPE_CHECKING:
    from ..llm import LLMClient


# 中枢类型注册表
ORCHESTRATOR_REGISTRY: Dict[str, type] = {
    "claude-code": ClaudeCodeOrchestrator,
    "opencode": OpenCodeOrchestrator,
    "openclaw": OpenClawOrchestrator,
    "api": APIOrchestrator,
}


def create_orchestrator(
    orchestrator_type: str,
    config: Optional[OrchestratorConfig] = None,
    llm_client: Optional[LLMClient] = None,
) -> OrchestratorClient:
    """
    创建中枢客户端

    Args:
        orchestrator_type: 中枢类型 (claude-code, opencode, openclaw, api)
        config: 中枢配置
        llm_client: LLM 客户端 (仅 api 类型需要)

    Returns:
        OrchestratorClient 实例

    Raises:
        ValueError: 未知的中枢类型
    """
    if orchestrator_type == "api":
        return APIOrchestrator(llm_client=llm_client, config=config)

    orchestrator_cls = ORCHESTRATOR_REGISTRY.get(orchestrator_type)
    if not orchestrator_cls:
        raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")

    return orchestrator_cls(config=config)


def discover_orchestrators() -> Dict[str, OrchestratorPresence]:
    """
    发现所有可用的中枢

    Returns:
        Dict[类型, 检测结果]
    """
    results = {}

    for orch_type, orch_cls in ORCHESTRATOR_REGISTRY.items():
        if orch_type == "api":
            # API 类型需要 LLMClient，跳过自动检测
            continue

        try:
            orchestrator = orch_cls()
            results[orch_type] = orchestrator.detect()
        except Exception as e:
            results[orch_type] = OrchestratorPresence(
                orchestrator_type=orch_type,
                detected=False,
                reason=f"error: {str(e)}",
            )

    return results


def get_available_orchestrators() -> List[str]:
    """
    获取所有可用的中枢类型列表

    Returns:
        已检测且认证通过的中枢类型列表
    """
    discovered = discover_orchestrators()
    return [
        orch_type
        for orch_type, presence in discovered.items()
        if presence.detected and presence.auth_ok
    ]


def get_best_orchestrator() -> str:
    """
    获取最佳可用的中枢

    优先级: claude-code > opencode > openclaw

    Returns:
        最佳可用的中枢类型，如果没有则返回 "api"
    """
    available = get_available_orchestrators()
    priority = ["claude-code", "opencode", "openclaw"]

    for orch_type in priority:
        if orch_type in available:
            return orch_type

    return "api"  # 回退到 API 方式


__all__ = [
    # 基类和类型
    "OrchestratorClient",
    "OrchestratorConfig",
    "OrchestratorPresence",
    "OrchestratorResponse",
    "OrchestratorMode",
    "OrchestratorCapability",
    # 具体实现
    "ClaudeCodeOrchestrator",
    "OpenCodeOrchestrator",
    "OpenClawOrchestrator",
    "APIOrchestrator",
    # 多 Provider 调度器
    "MultiProviderOrchestrator",
    "TaskType",
    "ProviderStats",
    "AgentSpec",
    # 工厂函数
    "create_orchestrator",
    "discover_orchestrators",
    "get_available_orchestrators",
    "get_best_orchestrator",
    # 注册表
    "ORCHESTRATOR_REGISTRY",
]