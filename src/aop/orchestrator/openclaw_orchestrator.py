"""
OpenClaw 作为中枢 Agent

通过 OpenClaw 客户端实现决策和执行。
OpenClaw 可以通过其 MCP 或 API 接口调用其他 Agent。
"""

from __future__ import annotations

import os
import platform
import subprocess
import shutil
import socket
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import OrchestratorClient
from .types import (
    OrchestratorConfig,
    OrchestratorPresence,
    OrchestratorResponse,
    OrchestratorMode,
    OrchestratorCapability,
)


# Windows 上常见的 npm 全局安装路径
NPM_GLOBAL_PATHS = [
    Path.home() / "AppData" / "Roaming" / "npm",
    Path.home() / ".npm-global" / "bin",
    Path("/usr/local/bin"),
    Path("/usr/bin"),
]

# OpenClaw 默认配置
DEFAULT_GATEWAY_PORT = 18789  # OpenClaw Gateway 默认端口
DEFAULT_CDP_PORT = 18792     # Chrome CDP 默认端口


def _find_binary(binary_name: str) -> Optional[str]:
    """查找 CLI 二进制文件"""
    result = shutil.which(binary_name)
    if result:
        return result

    if platform.system() == "Windows":
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            for ext in pathext:
                candidate = npm_path / f"{binary_name}{ext}"
                if candidate.exists():
                    return str(candidate)

    return None


def _is_port_open(port: int, host: str = "localhost") -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


class OpenClawOrchestrator(OrchestratorClient):
    """OpenClaw 中枢适配器"""

    BINARY_NAME = "openclaw"

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._binary_path: Optional[str] = None
        self._gateway_port = DEFAULT_GATEWAY_PORT
        self._cdp_port = DEFAULT_CDP_PORT

    @property
    def orchestrator_type(self) -> str:
        return "openclaw"

    @property
    def capabilities(self) -> List[OrchestratorCapability]:
        return [
            OrchestratorCapability.REQUIREMENT_CLARIFICATION,
            OrchestratorCapability.HYPOTHESIS_GENERATION,
            OrchestratorCapability.TASK_EXECUTION,
            OrchestratorCapability.CODE_REVIEW,
            OrchestratorCapability.LEARNING_EXTRACTION,
            OrchestratorCapability.MULTI_AGENT_DISPATCH,
        ]

    def detect(self) -> OrchestratorPresence:
        """检测 OpenClaw 是否可用"""
        # 1. 检查 openclaw CLI 是否安装
        binary = _find_binary(self.BINARY_NAME)
        cli_installed = binary is not None
        if binary:
            self._binary_path = binary

        # 2. 检查 Gateway 服务是否运行 (端口 18789)
        gateway_running = _is_port_open(self._gateway_port)

        # 3. 检查 CDP 端口是否可用（浏览器自动化，端口 18792）
        cdp_available = _is_port_open(self._cdp_port)

        # 判断整体状态
        if gateway_running:
            reason = "ready"
            detected = True
        elif cli_installed:
            reason = "cli_installed_gateway_not_running"
            detected = False
        else:
            reason = "not_installed"
            detected = False

        version = self._get_version() if binary else None

        return OrchestratorPresence(
            orchestrator_type=self.orchestrator_type,
            detected=detected,
            binary_path=binary,
            version=version,
            auth_ok=gateway_running,
            capabilities=self.capabilities,
            reason=reason,
        )

    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """通过 OpenClaw 进行决策"""
        raise NotImplementedError("OpenClaw integration pending")

    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """通过 OpenClaw 执行任务"""
        raise NotImplementedError("OpenClaw integration pending")

    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """OpenClaw 调度多 Agent"""
        raise NotImplementedError("OpenClaw integration pending")

    def _get_version(self) -> Optional[str]:
        """获取 OpenClaw 版本"""
        if not self._binary_path:
            return None
        try:
            result = subprocess.run(
                [self._binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0][:50]
        except Exception:
            pass
        return None


__all__ = [
    "OpenClawOrchestrator",
]
