"""
Orchestrator Base - 中枢 Agent 抽象基类

统一接口，支持：
- Claude Code CLI 作为中枢
- OpenCode CLI 作为中枢
- OpenClaw 作为中枢
- API 方式作为中枢 (兼容现有)

核心方法：
- detect(): 检测中枢是否可用
- complete(): 决策/规划类任务
- execute(): 执行类任务
- dispatch(): 多 Agent 调度
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .types import (
    OrchestratorMode,
    OrchestratorCapability,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorConfig,
)


class OrchestratorClient(ABC):
    """
    中枢 Agent 抽象基类

    统一接口，支持：
    - Claude Code CLI 作为中枢
    - OpenCode CLI 作为中枢
    - OpenClaw 作为中枢
    - API 方式作为中枢 (兼容现有)

    核心方法：
    - detect(): 检测中枢是否可用
    - complete(): 决策/规划类任务
    - execute(): 执行类任务
    - dispatch(): 多 Agent 调度
    """

    @property
    @abstractmethod
    def orchestrator_type(self) -> str:
        """中枢类型标识"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[OrchestratorCapability]:
        """中枢能力列表"""
        pass

    @abstractmethod
    def detect(self) -> OrchestratorPresence:
        """检测中枢是否可用"""
        pass

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        执行决策/规划类任务

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system: 系统提示
            **kwargs: 额外参数

        Returns:
            OrchestratorResponse: 响应结果
        """
        pass

    @abstractmethod
    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        执行任务

        Args:
            prompt: 任务描述
            repo_root: 仓库根目录
            target_paths: 目标路径
            **kwargs: 额外参数

        Returns:
            OrchestratorResponse: 执行结果
        """
        pass

    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """
        调度多个子 Agent 执行任务

        Args:
            prompt: 任务描述
            agents: 子 Agent 列表
            repo_root: 仓库根目录
            parallel: 是否并行执行
            **kwargs: 额外参数

        Returns:
            List[OrchestratorResponse]: 各 Agent 的执行结果
        """
        # 默认实现：顺序调用 execute()
        # 子类可以覆盖实现更高效的调度
        results = []
        for agent in agents:
            response = self.execute(
                prompt=f"[Agent: {agent}] {prompt}",
                repo_root=repo_root,
                **kwargs
            )
            results.append(response)
        return results

    def validate_connection(self) -> bool:
        """验证连接是否正常"""
        try:
            response = self.complete(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10
            )
            return bool(response.content)
        except Exception:
            return False

    def supports(self, capability: OrchestratorCapability) -> bool:
        """检查是否支持某能力"""
        return capability in self.capabilities


__all__ = [
    "OrchestratorClient",
]
