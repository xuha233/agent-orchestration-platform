"""OpenCode implementation of PrimaryAgent.

Uses the `opencode` CLI to interact with OpenCode.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from .base import AgentContext, PrimaryAgent


class OpenCodeAgent(PrimaryAgent):
    """PrimaryAgent implementation using OpenCode CLI.

    This agent uses the `opencode` command-line tool. Similar to
    Claude Code, it supports session management.

    Attributes:
        id: "opencode"
        name: "OpenCode"
        description: "OpenCode CLI agent"
    """

    id = "opencode"
    name = "OpenCode"
    description = "OpenCode CLI agent"

    def __init__(self) -> None:
        """Initialize the OpenCode agent."""
        self._session_id: Optional[str] = None
        self._opencode_dir = Path.home() / ".opencode"

    def is_available(self) -> bool:
        """Check if opencode CLI is available.

        Returns:
            True if the `opencode` binary is found in PATH
        """
        return shutil.which("opencode") is not None

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
        """
        # Build command - opencode uses similar flags to claude
        cmd = ["opencode", "-p", message]

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

        # Update session ID
        await self._update_session_id()

        return output

    async def _update_session_id(self) -> None:
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
