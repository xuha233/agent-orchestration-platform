"""
Claude Code CLI 作为中枢 Agent

通过 Claude Code CLI 实现决策和执行：
- complete(): 使用 ccr code --print 进行决策
- execute(): 使用 claude 进行代码修改
- dispatch(): 使用 claude 调度其他 Agent
"""

from __future__ import annotations

import json
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


class ClaudeCodeOrchestrator(OrchestratorClient):
    """Claude Code CLI 中枢适配器"""

    BINARY_NAME = "ccr"

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._binary_path: Optional[str] = None

    @property
    def orchestrator_type(self) -> str:
        return "claude-code"

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
        """检测 Claude Code CLI 是否可用"""
        binary = _find_binary(self.BINARY_NAME)
        if not binary:
            return OrchestratorPresence(
                orchestrator_type=self.orchestrator_type,
                detected=False,
                reason="binary_not_found",
            )

        self._binary_path = binary

        # 检测版本
        version = self._get_version()

        # 检测认证状态
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
        使用 Claude Code CLI 进行决策

        通过 `ccr code --print` 执行，不修改文件系统
        """
        prompt = self._build_prompt_from_messages(messages, system)

        binary = self._binary_path or self.BINARY_NAME
        cmd = [binary, "code", "--print",
            "--output-format", "json",
        ]

        # 添加配置参数
        if kwargs.get("max_tokens"):
            cmd.extend(["--max-tokens", str(kwargs["max_tokens"])])

        cwd = str(self.config.working_directory) if self.config.working_directory else "."

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=cwd,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code error: {result.stderr}")

        return self._parse_response(result.stdout)

    def execute(
        self,
        prompt: str,
        repo_root: str = ".",
        target_paths: Optional[List[str]] = None,
        **kwargs
    ) -> OrchestratorResponse:
        """
        使用 Claude Code CLI 执行任务

        允许 Claude Code 修改文件系统
        """
        binary = self._binary_path or self.BINARY_NAME
        cmd = [binary, "code", "--output-format", "json",
        ]

        # 添加权限配置
        if kwargs.get("permission_mode"):
            cmd.extend(["--permission-mode", kwargs["permission_mode"]])
        else:
            cmd.extend(["--permission-mode", "plan"])  # 默认计划模式

        # 添加目标路径限制
        if target_paths:
            cmd.extend(["--target-paths", ",".join(target_paths)])

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=repo_root,
        )

        return self._parse_response(result.stdout)

    def dispatch(
        self,
        prompt: str,
        agents: List[str],
        repo_root: str = ".",
        parallel: bool = True,
        **kwargs
    ) -> List[OrchestratorResponse]:
        """
        Claude Code 作为中枢调度其他 Agent

        使用 Claude Code 的 MCP 或工具调用能力来调度其他 Agent
        """
        dispatch_prompt = f"""你是一个多 Agent 调度器。现在需要完成以下任务：

{prompt}

你需要调度以下 Agent 来完成这个任务：
{chr(10).join(f'- {agent}' for agent in agents)}

请分析任务，分配给合适的 Agent，并汇总结果。
"""

        response = self.execute(
            prompt=dispatch_prompt,
            repo_root=repo_root,
            **kwargs
        )

        return [response]

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

    def _parse_response(self, stdout: str) -> OrchestratorResponse:
        """解析 Claude Code 输出"""
        try:
            data = json.loads(stdout)
            return OrchestratorResponse(
                content=data.get("content", stdout),
                model=data.get("model", "claude-unknown"),
                orchestrator_type=self.orchestrator_type,
                mode=OrchestratorMode.FULL,
                usage=data.get("usage", {}),
                finish_reason=data.get("stop_reason", "stop"),
                raw=data,
            )
        except json.JSONDecodeError:
            return OrchestratorResponse(
                content=stdout,
                model="claude-unknown",
                orchestrator_type=self.orchestrator_type,
                mode=OrchestratorMode.FULL,
            )

    def _get_version(self) -> Optional[str]:
        """获取 Claude Code 版本"""
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

    def _check_auth(self) -> tuple[bool, str]:
        """
        检查认证状态

        通过运行一个简单的测试命令来验证 CLI 是否可用。
        注意：这个检查不仅检查认证，还验证 CLI 是否能正常工作。
        """
        if not self._binary_path:
            return False, "binary_not_found"

        try:
            # 使用 --print 运行一个简单的 prompt 来验证
            result = subprocess.run(
                [self._binary_path, "code", "--print", "Say 'ok'"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # 成功执行，CLI 可用
                return True, "authenticated"

            # 检查是否是认证相关的错误
            stderr_lower = result.stderr.lower()
            stdout_lower = result.stdout.lower()

            # 明确的认证错误模式
            auth_error_patterns = [
                "not authenticated",
                "authentication required",
                "please run",
                "login required",
                "no api key",
                "anthropic_api_key",
                "needs auth",
            ]

            for pattern in auth_error_patterns:
                if pattern in stderr_lower or pattern in stdout_lower:
                    return False, "not_authenticated"

            # 非 0 返回码但没有明确的认证错误
            # 可能是网络问题、API 限制等，暂时认为可用
            return True, "available"

        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, f"error: {str(e)[:50]}"


__all__ = [
    "ClaudeCodeOrchestrator",
]
