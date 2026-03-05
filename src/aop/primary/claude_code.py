"""Claude Code implementation of PrimaryAgent.

Uses the `claude` CLI to interact with Claude Code.
"""

from __future__ import annotations

import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from .base import AgentContext, PrimaryAgent


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


class ClaudeCodeAgent(PrimaryAgent):
    """PrimaryAgent implementation using Claude Code CLI.

    This agent uses the `claude` command-line tool to interact with
    Claude Code. It supports session management via --resume flag.

    Attributes:
        id: "claude_code"
        name: "Claude Code"
        description: "Anthropic's Claude Code CLI agent"
    """

    id = "claude_code"
    name = "Claude Code"
    description = "Anthropic's Claude Code CLI agent"

    def __init__(self) -> None:
        """Initialize the Claude Code agent."""
        self._session_id: Optional[str] = None
        self._claude_projects_dir = Path.home() / ".claude" / "projects"
        self._binary_path: Optional[str] = None

    def is_available(self) -> bool:
        """Check if claude CLI is available.

        Returns:
            True if the `claude` binary is found in PATH
        """
        self._binary_path = _find_binary("claude")
        return self._binary_path is not None

    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        """Chat with Claude Code.

        Args:
            message: The user message to send
            context: Execution context with workspace and session info
            stream: Whether to stream the response (default True)

        Returns:
            Complete response text

        Raises:
            RuntimeError: If the command fails or returns empty output
        """
        # Build command
        binary = self._binary_path or _find_binary("claude") or "claude"
        cmd = [binary, "-p", message, "--dangerously-skip-permissions"]

        # Add resume flag if we have a session
        if self._session_id:
            cmd.extend(["--resume", self._session_id])
        elif context.session_id:
            cmd.extend(["--resume", context.session_id])

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
            stderr_output = result.stderr

            # Check for errors
            if result.returncode != 0:
                error_msg = stderr_output.strip() or f"Exit code: {result.returncode}"
                raise RuntimeError(f"Claude Code error: {error_msg}")

            # Check for empty output with stderr content
            if not output.strip() and stderr_output.strip():
                raise RuntimeError(f"Claude Code stderr: {stderr_output.strip()}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code command timed out after 5 minutes")

        # Try to extract session ID from output or projects directory
        self._update_session_id(context.workspace_path)

        return output

    def _update_session_id(self, workspace_path: Path) -> None:
        """Update session ID from the Claude projects directory.

        Claude Code stores session data in ~/.claude/projects/<encoded-path>/.

        Args:
            workspace_path: The workspace path to look up
        """
        if not self._claude_projects_dir.exists():
            return

        # Encode the workspace path similar to how Claude does it
        # Claude uses a base64-like encoding of the path
        try:
            # Look for the most recent session directory
            # This is a simplified approach - actual implementation
            # might need to match Claude's exact encoding
            path_str = str(workspace_path.absolute())
            # Simple hash-like approach for finding matching directory
            for project_dir in self._claude_projects_dir.iterdir():
                if project_dir.is_dir():
                    # Check if this project dir matches our workspace
                    # Claude encodes the path in the directory name
                    if path_str.replace("\\", "/").replace(":", "") in project_dir.name.replace("-", ""):
                        # Find the most recent session file
                        session_files = list(project_dir.glob("*.json"))
                        if session_files:
                            latest = max(session_files, key=lambda p: p.stat().st_mtime)
                            self._session_id = latest.stem
                            return
        except Exception:
            # If we can't determine the session ID, that's OK
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
