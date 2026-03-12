"""
Orchestrator Types - 中枢相关类型定义

定义中枢 Agent 的核心类型：
- OrchestratorMode: 中枢工作模式
- OrchestratorCapability: 中枢能力
- OrchestratorPresence: 中枢检测结果
- OrchestratorResponse: 中枢响应
- OrchestratorConfig: 中枢配置
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable


class OrchestratorMode(Enum):
    """中枢工作模式"""
    DECISION = "decision"      # 仅决策/规划
    EXECUTION = "execution"    # 仅执行
    FULL = "full"              # 决策+执行


class OrchestratorCapability(Enum):
    """中枢能力"""
    REQUIREMENT_CLARIFICATION = "requirement_clarification"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    TASK_EXECUTION = "task_execution"
    CODE_REVIEW = "code_review"
    LEARNING_EXTRACTION = "learning_extraction"
    MULTI_AGENT_DISPATCH = "multi_agent_dispatch"


@dataclass
class OrchestratorPresence:
    """中枢检测结果"""
    orchestrator_type: str
    detected: bool
    binary_path: Optional[str] = None
    version: Optional[str] = None
    auth_ok: bool = False
    capabilities: List[OrchestratorCapability] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "orchestrator_type": self.orchestrator_type,
            "detected": self.detected,
            "binary_path": self.binary_path,
            "version": self.version,
            "auth_ok": self.auth_ok,
            "capabilities": [c.value for c in self.capabilities],
            "reason": self.reason,
        }


@dataclass
class OrchestratorResponse:
    """中枢响应结果"""
    content: str
    model: str
    orchestrator_type: str
    mode: OrchestratorMode
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    artifacts: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "model": self.model,
            "orchestrator_type": self.orchestrator_type,
            "mode": self.mode.value,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "artifacts": self.artifacts,
            "raw": self.raw,
        }


@dataclass
class OrchestratorConfig:
    """中枢配置"""
    mode: OrchestratorMode = OrchestratorMode.FULL
    working_directory: Optional[Path] = None
    timeout: int = 600
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 4096

    # 会话恢复
    session_id: Optional[str] = None

    # 多 Agent 调度配置
    sub_agents: List[str] = field(default_factory=lambda: ["claude", "codex"])
    parallel_execution: bool = True
    max_parallel: int = 5

    # 回调
    progress_callback: Optional[Callable[[str, str], None]] = None


__all__ = [
    "OrchestratorMode",
    "OrchestratorCapability",
    "OrchestratorPresence",
    "OrchestratorResponse",
    "OrchestratorConfig",
]
