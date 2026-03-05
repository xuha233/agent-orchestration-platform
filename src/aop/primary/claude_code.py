"""Claude Code implementation of PrimaryAgent.

Uses the `claude` CLI to interact with Claude Code.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from .base import AgentContext, PrimaryAgent


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

    def is_available(self) -> bool:
        """Check if claude CLI is available.

        Returns:
            True if the `claude` binary is found in PATH
        """
        return shutil.which("claude") is not None

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
        cmd = ["claude", "-p", message, "--dangerously-skip-permissions"]

        # Add resume flag if we have a session
        if self._session_id:
            cmd.extend(["--resume", self._session_id])
        elif context.session_id:
            cmd.extend(["--resume", context.session_id])

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(context.workspace_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Read output
        stdout_data, stderr_data = await process.communicate()
        output = stdout_data.decode("utf-8")
        stderr_output = stderr_data.decode("utf-8")

        # Check for errors
        if process.returncode != 0:
            error_msg = stderr_output.strip() or f"Exit code: {process.returncode}"
            raise RuntimeError(f"Claude Code error: {error_msg}")

        # Check for empty output with stderr content
        if not output.strip() and stderr_output.strip():
            raise RuntimeError(f"Claude Code stderr: {stderr_output.strip()}")

        # Try to extract session ID from output or projects directory
        await self._update_session_id(context.workspace_path)

        return output

    async def _update_session_id(self, workspace_path: Path) -> None:
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
