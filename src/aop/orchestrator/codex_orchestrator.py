"""
Codex CLI 作为中枢 Agent

通过 Codex CLI 实现决策和执行
"""

from __future__ import annotations

import os
import sys
import platform
import subprocess
import shutil
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
def _get_npm_global_paths():
    """获取 npm 全局路径（跨平台）"""
    paths = []
    if sys.platform == "win32":
        paths.append(Path.home() / "AppData" / "Roaming" / "npm")
    else:
        paths.extend([
            Path("/usr/local/bin"),
            Path("/usr/bin"),
        ])
    # 通用路径
    npm_global = Path.home() / ".npm-global" / "bin"
    if npm_global.exists():
        paths.append(npm_global)
    return paths


NPM_GLOBAL_PATHS = _get_npm_global_paths()


def _find_binary(binary_name: str) -> Optional[str]:
    """
    查找 CLI 二进制文件，支持 Windows 的 .cmd/.bat 扩展名

    在 Windows 上，npm 安装的 CLI 通常是 .cmd 文件，
    shutil.which() 在某些环境下可能无法正确找到它们。
    """
    # 首先尝试标准查找
    result = shutil.which(binary_name)
    if result:
        return result

    # 在 Windows 上额外检查常见路径
    if platform.system() == "Windows":
        # 检查 PATHEXT 环境变量指定的扩展名
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD" if sys.platform == "win32" else "").split(";") if sys.platform == "win32" else [""]

        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            for ext in pathext:
                candidate = npm_path / f"{binary_name}{ext}"
                if candidate.exists():
                    return str(candidate)

        # 直接检查 .cmd 扩展名（npm 最常见的情况）
        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            candidate = npm_path / f"{binary_name}.cmd"
            if candidate.exists():
                return str(candidate)

    return None


class CodexOrchestrator(OrchestratorClient):
    """Codex CLI 中枢适配器"""

    BINARY_NAME = "codex"

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._binary_path: Optional[str] = None

    @property
    def orchestrator_type(self) -> str:
        return "codex"

    @property
    def capabilities(self) -> List[OrchestratorCapability]:
        return [
            OrchestratorCapability.TASK_EXECUTION,
            OrchestratorCapability.CODE_REVIEW,
        ]

    def detect(self) -> OrchestratorPresence:
        """检测 Codex CLI 是否可用"""
        binary = _find_binary(self.BINARY_NAME)
        if not binary:
            return OrchestratorPresence(
                orchestrator_type=self.orchestrator_type,
                detected=False,
                reason="binary_not_found",
            )

        self._binary_path = binary
        version = self._get_version()
        auth_ok, auth_reason = self._check_auth()

        return OrchestratorPresence(
            orchestrator_type=self.orchestrator_type,
            detected=True,
            binary_path=binary,
            version=version,
            auth_ok=auth_ok,
            capabilities=self.capabilities,
            reason=auth_reason,
        )

    def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        使用 Codex CLI 进行决策

        Codex 没有 --print 模式，使用 exec 模式作为替代
        """
        prompt = self._build_prompt_from_messages(messages, system)
        return self.execute(prompt, **kwargs)

    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        使用 Codex CLI 执行任务

        Args:
            prompt: 任务提示
            repo_root: 仓库根目录
            target_paths: 目标路径限制（未使用）
            session_id: 会话 ID，用于恢复之前的会话
            **kwargs: 其他参数
                - model: 模型选择 (如 o3, o4-mini)
                - json_output: 是否使用 JSON 输出 (默认 True)
                - sandbox: 沙箱模式 (默认 workspace-write)
        """
        # 确保 binary_path 已初始化
        if not self._binary_path:
            self.detect()
        binary = self._binary_path or self.BINARY_NAME

        # 构建命令
        cmd = [binary, "exec", "--full-auto"]

        # JSON 输出
        if kwargs.get("json_output", True):
            cmd.append("--json")

        # 工作目录
        if repo_root != ".":
            cmd.extend(["--cd", repo_root])

        # 模型选择
        if kwargs.get("model"):
            cmd.extend(["--model", kwargs["model"]])

        # 沙箱模式
        sandbox = kwargs.get("sandbox", "workspace-write")
        if sandbox:
            cmd.extend(["--sandbox", sandbox])

        # 会话恢复
        if session_id:
            cmd.extend(["--resume", session_id])

        cwd = str(self.config.working_directory) if self.config.working_directory else repo_root

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=cwd,
            encoding='utf-8',
            errors='replace',
        )

        return OrchestratorResponse(
            content=result.stdout,
            model=kwargs.get("model", "codex"),
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.EXECUTION,
            raw={"returncode": result.returncode, "stderr": result.stderr},
        )

    def review(
        self,
        prompt: str = "",
        repo_root: str = ".",
        **kwargs
    ) -> OrchestratorResponse:
        """
        使用 Codex CLI 进行代码审查

        Args:
            prompt: 审查提示
            repo_root: 仓库根目录
            **kwargs: 其他参数
                - uncommitted: 审查未提交的更改
                - base: 对比基准分支
        """
        # 确保 binary_path 已初始化
        if not self._binary_path:
            self.detect()
        binary = self._binary_path or self.BINARY_NAME

        cmd = [binary, "review"]

        if kwargs.get("uncommitted"):
            cmd.append("--uncommitted")
        elif kwargs.get("base"):
            cmd.extend(["--base", kwargs["base"]])

        if prompt:
            cmd.append(prompt)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=repo_root,
            encoding='utf-8',
            errors='replace',
        )

        return OrchestratorResponse(
            content=result.stdout,
            model="codex",
            orchestrator_type=self.orchestrator_type,
            mode=OrchestratorMode.EXECUTION,
            raw={"returncode": result.returncode, "stderr": result.stderr},
        )

    def _build_prompt_from_messages(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None
    ) -> str:
        """从消息列表构建提示"""
        parts = []
        if system:
            parts.append(f"System: {system}")
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.capitalize()}: {content}")
        return "\n\n".join(parts)

    def _get_version(self) -> Optional[str]:
        """获取 Codex 版本"""
        if not self._binary_path:
            return None
        try:
            result = subprocess.run(
                [self._binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace',
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0][:50]
        except Exception:
            pass
        return None

    def _check_auth(self) -> tuple[bool, str]:
        """
        检查认证状态

        通过 'codex login status' 检查是否已登录。
        """
        if not self._binary_path:
            return False, "binary_not_found"

        try:
            result = subprocess.run(
                [self._binary_path, "login", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace',
            )

            output = (result.stdout + result.stderr).lower()

            if "logged in" in output:
                return True, "authenticated"
            elif "not logged in" in output or "login required" in output:
                return False, "not_authenticated"

            return False, "unknown"

        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, f"error: {str(e)[:50]}"


__all__ = [
    "CodexOrchestrator",
]
