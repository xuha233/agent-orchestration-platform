"""
多 Provider 混合调度器

统一调度器，支持根据任务类型自动选择或手动指定 provider：
- claude-code: 强推理，适合复杂任务
- opencode: 快速，便宜
- openclaw: 本地 Gateway
- api: 直接 API 调用

支持：
- 跨 provider 调度多个 Agent
- 根据任务类型自动选择最佳 provider
- 故障转移
- 统计信息跟踪
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from .base import OrchestratorClient
from .types import (
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)
from .claude_code_orchestrator import ClaudeCodeOrchestrator
from .opencode_orchestrator import OpenCodeOrchestrator
from .openclaw_orchestrator import OpenClawOrchestrator
from .api_orchestrator import APIOrchestrator


class TaskType(Enum):
    """任务类型"""
    CODE_REVIEW = "code_review"           # 代码审查
    QUICK_IMPLEMENT = "quick_implement"   # 快速实现
    COMPLEX_REFACTOR = "complex_refactor" # 复杂重构
    REQUIREMENT_CLARIFICATION = "requirement_clarification"  # 需求澄清
    HYPOTHESIS_TEST = "hypothesis_test"   # 假设验证
    LEARNING = "learning"                 # 学习提取
    GENERAL = "general"                   # 通用任务


@dataclass
class ProviderStats:
    """Provider 统计信息"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_time_ms: float = 0.0
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def avg_time_ms(self) -> float:
        """平均响应时间"""
        if self.total_calls == 0:
            return 0.0
        return self.total_time_ms / self.total_calls

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.success_rate, 4),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "last_error": self.last_error,
        }


@dataclass
class AgentSpec:
    """Agent 规格"""
    name: str
    provider: Optional[str] = None  # None 表示自动选择
    task_type: Optional[TaskType] = None
    fallback_provider: Optional[str] = None  # 故障转移目标


class MultiProviderOrchestrator:
    """
    多 Provider 混合调度器

    支持根据任务类型自动选择或手动指定 provider，实现跨 provider 调度。

    使用示例:
        orchestrator = MultiProviderOrchestrator(default_provider="auto")

        # 单个任务，自动选择 provider
        response = await orchestrator.dispatch_single(
            prompt="Review this code",
            task_type=TaskType.CODE_REVIEW
        )

        # 多个 Agent，跨 provider 调度
        results = await orchestrator.dispatch(
            prompt="Implement feature X",
            agents=[
                {"name": "reviewer", "provider": "opencode"},
                {"name": "implementer", "provider": "claude-code"},
            ]
        )
    """

    # 任务类型 -> 推荐 provider 的映射
    TASK_PROVIDER_MAP: Dict[TaskType, List[str]] = {
        TaskType.CODE_REVIEW: ["claude-code", "opencode"],
        TaskType.QUICK_IMPLEMENT: ["opencode", "claude-code"],
        TaskType.COMPLEX_REFACTOR: ["claude-code", "opencode"],
        TaskType.REQUIREMENT_CLARIFICATION: ["claude-code", "opencode", "openclaw"],
        TaskType.HYPOTHESIS_TEST: ["claude-code", "opencode"],
        TaskType.LEARNING: ["opencode", "claude-code"],
        TaskType.GENERAL: ["opencode", "claude-code", "openclaw"],
    }

    # Provider 优先级（故障转移顺序）
    PROVIDER_PRIORITY = ["claude-code", "opencode", "openclaw", "api"]

    def __init__(
        self,
        default_provider: str = "auto",
        config: Optional[OrchestratorConfig] = None,
        llm_client: Optional[Any] = None,
    ):
        """
        初始化多 Provider 调度器

        Args:
            default_provider: 默认 provider ("auto" 表示自动选择)
            config: 中枢配置
            llm_client: LLM 客户端（仅 api provider 需要）
        """
        self.default_provider = default_provider
        self.config = config or OrchestratorConfig()
        self._llm_client = llm_client

        # 延迟初始化 providers
        self._providers: Dict[str, OrchestratorClient] = {}
        self._provider_presence: Dict[str, OrchestratorPresence] = {}

        # 统计信息
        self._stats: Dict[str, ProviderStats] = {
            "claude-code": ProviderStats(),
            "opencode": ProviderStats(),
            "openclaw": ProviderStats(),
            "api": ProviderStats(),
        }

        # 回调
        self._progress_callback: Optional[Callable[[str, str, str], None]] = None

    def set_progress_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """
        设置进度回调

        Args:
            callback: 回调函数 (agent_name, provider, status)
        """
        self._progress_callback = callback

    def _get_provider(self, provider_type: str) -> Optional[OrchestratorClient]:
        """获取或创建 provider 实例"""
        if provider_type in self._providers:
            return self._providers[provider_type]

        # 创建新实例
        try:
            if provider_type == "claude-code":
                provider = ClaudeCodeOrchestrator(config=self.config)
            elif provider_type == "opencode":
                provider = OpenCodeOrchestrator(config=self.config)
            elif provider_type == "openclaw":
                provider = OpenClawOrchestrator(config=self.config)
            elif provider_type == "api":
                if not self._llm_client:
                    return None
                provider = APIOrchestrator(llm_client=self._llm_client, config=self.config)
            else:
                return None

            self._providers[provider_type] = provider
            return provider
        except Exception:
            return None

    def _detect_provider(self, provider_type: str) -> OrchestratorPresence:
        """检测 provider 是否可用"""
        if provider_type in self._provider_presence:
            return self._provider_presence[provider_type]

        provider = self._get_provider(provider_type)
        if not provider:
            presence = OrchestratorPresence(
                orchestrator_type=provider_type,
                detected=False,
                reason="provider_not_available"
            )
        else:
            presence = provider.detect()

        self._provider_presence[provider_type] = presence
        return presence

    def select_provider(self, task_type: TaskType) -> str:
        """
        根据任务类型选择最佳 provider

        Args:
            task_type: 任务类型

        Returns:
            最佳可用的 provider 类型
        """
        # 获取推荐顺序
        recommended = self.TASK_PROVIDER_MAP.get(task_type, self.PROVIDER_PRIORITY)

        # 按推荐顺序检测可用性
        for provider_type in recommended:
            presence = self._detect_provider(provider_type)
            if presence.detected and (presence.auth_ok or provider_type == "api"):
                return provider_type

        # 回退到第一个可用的
        for provider_type in self.PROVIDER_PRIORITY:
            presence = self._detect_provider(provider_type)
            if presence.detected:
                return provider_type

        # 最后回退到 api
        return "api"

    def get_available_providers(self) -> List[str]:
        """获取所有可用的 provider"""
        available = []
        for provider_type in self.PROVIDER_PRIORITY:
            presence = self._detect_provider(provider_type)
            if presence.detected:
                available.append(provider_type)
        return available

    async def dispatch_single(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        provider: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> OrchestratorResponse:
        """
        调度单个任务

        Args:
            prompt: 任务描述
            task_type: 任务类型
            provider: 指定 provider（None 表示自动选择）
            fallback: 是否启用故障转移
            **kwargs: 传递给 provider 的额外参数

        Returns:
            OrchestratorResponse: 执行结果
        """
        # 确定 provider
        if provider == "auto" or provider is None:
            provider = self.select_provider(task_type)

        # 获取 provider 实例
        provider_client = self._get_provider(provider)
        if not provider_client:
            if fallback:
                # 故障转移
                return await self._fallback_dispatch(prompt, task_type, exclude=[provider], **kwargs)
            raise RuntimeError(f"Provider '{provider}' not available")

        # 执行任务
        start_time = time.time()
        stats = self._stats.get(provider, ProviderStats())

        try:
            stats.total_calls += 1

            # 调用 execute
            response = provider_client.execute(
                prompt=prompt,
                repo_root=kwargs.get("repo_root", "."),
                target_paths=kwargs.get("target_paths"),
                **kwargs
            )

            stats.successful_calls += 1
            stats.total_time_ms += (time.time() - start_time) * 1000

            if self._progress_callback:
                self._progress_callback("single", provider, "success")

            return response

        except Exception as e:
            stats.failed_calls += 1
            stats.last_error = str(e)[:200]
            stats.total_time_ms += (time.time() - start_time) * 1000

            if self._progress_callback:
                self._progress_callback("single", provider, f"error: {str(e)[:50]}")

            if fallback:
                return await self._fallback_dispatch(
                    prompt, task_type, exclude=[provider], **kwargs
                )

            raise

    async def _fallback_dispatch(
        self,
        prompt: str,
        task_type: TaskType,
        exclude: List[str],
        **kwargs
    ) -> OrchestratorResponse:
        """故障转移调度"""
        for provider_type in self.PROVIDER_PRIORITY:
            if provider_type in exclude:
                continue

            provider = self._get_provider(provider_type)
            if not provider:
                continue

            presence = self._detect_provider(provider_type)
            if not presence.detected:
                continue

            try:
                return provider.execute(
                    prompt=prompt,
                    repo_root=kwargs.get("repo_root", "."),
                    **kwargs
                )
            except Exception:
                continue

        raise RuntimeError("No available provider for fallback")

    async def dispatch(
        self,
        prompt: str,
        agents: List[Dict[str, str]],
        parallel: bool = True,
        **kwargs
    ) -> Dict[str, OrchestratorResponse]:
        """
        调度多个 Agent，支持跨 provider

        Args:
            prompt: 任务描述
            agents: Agent 列表，格式: [{"name": "reviewer", "provider": "opencode"}, ...]
            parallel: 是否并行执行
            **kwargs: 传递给 provider 的额外参数

        Returns:
            Dict[agent_name, OrchestratorResponse]: 各 Agent 的执行结果

        示例:
            results = await orchestrator.dispatch(
                prompt="Review and implement feature X",
                agents=[
                    {"name": "reviewer", "provider": "opencode"},
                    {"name": "implementer", "provider": "claude-code"},
                ],
                parallel=True
            )
        """
        results: Dict[str, OrchestratorResponse] = {}

        if parallel:
            # 并行执行
            tasks = []
            agent_names = []

            for agent_spec in agents:
                name = agent_spec.get("name", "unknown")
                provider = agent_spec.get("provider", "auto")
                task_type_str = agent_spec.get("task_type", "general")

                try:
                    task_type = TaskType(task_type_str) if isinstance(task_type_str, str) else TaskType.GENERAL
                except ValueError:
                    task_type = TaskType.GENERAL

                task = self.dispatch_single(
                    prompt=f"[Agent: {name}] {prompt}",
                    task_type=task_type,
                    provider=provider,
                    **kwargs
                )
                tasks.append(task)
                agent_names.append(name)

            # 等待所有任务完成
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for name, response in zip(agent_names, responses):
                if isinstance(response, Exception):
                    results[name] = OrchestratorResponse(
                        content=f"Error: {str(response)}",
                        model="error",
                        orchestrator_type="error",
                        mode=OrchestratorMode.FULL,
                        finish_reason="error"
                    )
                else:
                    results[name] = response

        else:
            # 顺序执行
            for agent_spec in agents:
                name = agent_spec.get("name", "unknown")
                provider = agent_spec.get("provider", "auto")
                task_type_str = agent_spec.get("task_type", "general")

                try:
                    task_type = TaskType(task_type_str) if isinstance(task_type_str, str) else TaskType.GENERAL
                except ValueError:
                    task_type = TaskType.GENERAL

                if self._progress_callback:
                    self._progress_callback(name, provider or "auto", "started")

                try:
                    response = await self.dispatch_single(
                        prompt=f"[Agent: {name}] {prompt}",
                        task_type=task_type,
                        provider=provider,
                        **kwargs
                    )
                    results[name] = response
                except Exception as e:
                    results[name] = OrchestratorResponse(
                        content=f"Error: {str(e)}",
                        model="error",
                        orchestrator_type="error",
                        mode=OrchestratorMode.FULL,
                        finish_reason="error"
                    )

        return results

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 provider 的统计信息"""
        return {
            provider: stats.to_dict()
            for provider, stats in self._stats.items()
        }

    def get_best_provider_for_task(self, task_type: TaskType) -> str:
        """
        获取特定任务类型的最佳 provider

        结合可用性和历史成功率选择
        """
        recommended = self.TASK_PROVIDER_MAP.get(task_type, self.PROVIDER_PRIORITY)

        best_provider = None
        best_score = -1

        for provider_type in recommended:
            presence = self._detect_provider(provider_type)
            if not presence.detected:
                continue

            stats = self._stats.get(provider_type, ProviderStats())

            # 计算分数：成功率 * 0.7 + 可用性 0.3
            score = stats.success_rate * 0.7 + 0.3

            if score > best_score:
                best_score = score
                best_provider = provider_type

        return best_provider or recommended[0]

    def reset_stats(self) -> None:
        """重置统计信息"""
        for provider in self._stats:
            self._stats[provider] = ProviderStats()

    def refresh_providers(self) -> Dict[str, OrchestratorPresence]:
        """刷新所有 provider 的状态"""
        self._provider_presence.clear()
        results = {}

        for provider_type in self.PROVIDER_PRIORITY:
            results[provider_type] = self._detect_provider(provider_type)

        return results


__all__ = [
    "MultiProviderOrchestrator",
    "TaskType",
    "ProviderStats",
    "AgentSpec",
]
