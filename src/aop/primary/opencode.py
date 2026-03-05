"""OpenCode implementation of PrimaryAgent.

Uses the `opencode` CLI to interact with OpenCode.
"""

from __future__ import annotations

import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from .base import AgentContext, PrimaryAgent
from .memory_extractor import extract_and_save_memory


# Windows 上常见的 npm 全局安装路径
NPM_GLOBAL_PATHS = [
    Path.home() / "AppData" / "Roaming" / "npm",
    Path.home() / ".npm-global" / "bin",
    Path("/usr/local/bin"),
    Path("/usr/bin"),
]


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
        import os
        # 检查 PATHEXT 环境变量指定的扩展名
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")

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


def _load_context_files(workspace_path: Path) -> str:
    """加载项目上下文文件（SOUL.md, PROJECT_MEMORY.md, WORKFLOW.md, TEAM.md）
    
    这些文件帮助 Agent 理解项目背景、角色定位和工作流程。
    """
    context_dir = workspace_path / '.aop'
    if not context_dir.exists():
        return ''
    
    context_parts = []
    for filename in ['SOUL.md', 'PROJECT_MEMORY.md', 'WORKFLOW.md', 'TEAM.md']:
        filepath = context_dir / filename
        if filepath.exists():
            try:
                file_content = filepath.read_text(encoding='utf-8')
                context_parts.append(f'=== {filename} ===\n{file_content}\n')
            except Exception:
                pass
    
    return '\n'.join(context_parts)


class OpenCodeAgent(PrimaryAgent):
    """PrimaryAgent implementation using OpenCode CLI.

    This agent uses the `opencode` command-line tool. Similar to
    Claude Code, it supports session management.

    Attributes:
        id: "opencode"
        name: "OpenCode"
        description = "OpenCode CLI agent"
    """

    id = "opencode"
    name = "OpenCode"
    description = "OpenCode CLI agent"

    def __init__(self) -> None:
        """Initialize the OpenCode agent."""
        self._session_id: Optional[str] = None
        self._opencode_dir = Path.home() / ".opencode"
        self._binary_path: Optional[str] = None

    def is_available(self) -> bool:
        """Check if opencode CLI is available.

        Returns:
            True if the `opencode` binary is found in PATH
        """
        self._binary_path = _find_binary("opencode")
        return self._binary_path is not None

    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        """Chat with OpenCode.

        Args:
            message: The user message to send
            context: Execution context with workspace and session info
            stream: Whether to stream the response (default True)

        Returns:
            Complete response text

        Raises:
            RuntimeError: If the command fails
        """
        # 加载项目上下文
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        # Build command - opencode uses 'run' subcommand
        binary = self._binary_path or _find_binary("opencode") or "opencode"
        cmd = [binary, "run", message]

        # Add session flag if we have a session
        # OpenCode uses -s for session, -c for continue last session
        if self._session_id:
            cmd.extend(["-s", self._session_id])
        elif context.session_id:
            cmd.extend(["-s", context.session_id])

        # 使用同步 subprocess.run 替代 asyncio.create_subprocess_exec
        # 这在 Windows 上更稳定，特别是在 Streamlit 环境中
        try:
            result = subprocess.run(
                cmd,
                cwd=str(context.workspace_path),
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
            )

            output = result.stdout

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"Exit code: {result.returncode}"
                raise RuntimeError(f"OpenCode error: {error_msg}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("OpenCode command timed out after 5 minutes")

        # Update session ID
        self._update_session_id()

        # 自动提取记忆
        try:
            # 保存原始消息（去除上下文前缀）
            original_message = message
            if "【用户消息】" in message:
                original_message = message.split("【用户消息】\n")[-1]
            extract_and_save_memory(original_message, output, context.workspace_path)
        except Exception:
            # 记忆提取失败不应影响主流程
            pass

        return output

    def _update_session_id(self) -> None:
        """Update session ID from the OpenCode directory.

        OpenCode may store session data in ~/.opencode/.
        """
        if not self._opencode_dir.exists():
            return

        try:
            # Look for session files in the opencode directory
            session_files = list(self._opencode_dir.glob("**/session*.json"))
            if session_files:
                latest = max(session_files, key=lambda p: p.stat().st_mtime)
                self._session_id = latest.stem
        except Exception:
            pass

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID.

        Returns:
            The current session ID if one exists, None otherwise
        """
        return self._session_id

    def resume_session(self, session_id: str) -> bool:
        """Resume a previous session.

        Args:
            session_id: The session ID to resume

        Returns:
            True if the session ID was set successfully
        """
        self._session_id = session_id
        return True

    def clear_session(self) -> None:
        """Clear the current session."""
        self._session_id = None
