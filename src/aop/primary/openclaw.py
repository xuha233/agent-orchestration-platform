"""OpenClaw agent implementation for AOP.

Provides integration with OpenClaw as a primary agent.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
from pathlib import Path
from typing import AsyncIterator, Optional, Callable

from .base import AgentContext, PrimaryAgent


class OpenClawAgent(PrimaryAgent):
    """OpenClaw primary agent implementation.

    OpenClaw is an AI assistant framework that can be used as a primary
    agent in the AOP system. This implementation checks for OpenClaw
    Gateway availability and provides chat functionality via the TUI.
    """

    id = "openclaw"
    name = "OpenClaw"
    description = "OpenClaw AI Assistant (TUI/Gateway)"

    GATEWAY_PORT = 18789  # Gateway WebSocket port

    def __init__(self) -> None:
        """Initialize the OpenClaw agent."""
        self._session_id: Optional[str] = None

    def is_available(self) -> bool:
        """Check if OpenClaw is available on the current system.

        Checks for:
        1. openclaw CLI binary
        2. Gateway running on port 18789

        Returns:
            True if OpenClaw can be used, False otherwise
        """
        # Check if openclaw CLI is installed
        if not shutil.which("openclaw"):
            return False

        # Check if Gateway is running
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", self.GATEWAY_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        """Chat with the OpenClaw agent.

        Note: OpenClaw chat is typically done via TUI or Gateway.
        This implementation provides a placeholder for programmatic access.

        Args:
            message: The user message to send
            context: Execution context with workspace and session info
            stream: Whether to stream the response (default True)

        Returns:
            Response text (placeholder - actual chat done via TUI)
        """
        # OpenClaw chat is typically done via TUI or Web interface
        # This is a placeholder for programmatic access
        return "OpenClaw chat is available via TUI or Web interface. Use Dashboard to launch."

    async def chat_stream(
        self,
        message: str,
        context: AgentContext,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[str]:
        """Chat with the agent and yield tokens as they arrive.

        Note: Placeholder implementation - actual chat done via TUI.

        Args:
            message: The user message to send
            context: Execution context with workspace and session info
            on_token: Optional callback for each token

        Yields:
            Response text
        """
        response = await self.chat(message, context, stream=False)
        if on_token:
            on_token(response)
        yield response

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID.

        Returns:
            The current session ID if one is active, None otherwise
        """
        return self._session_id

    def resume_session(self, session_id: str) -> bool:
        """Resume a previous session.

        Args:
            session_id: The session ID to resume

        Returns:
            True (always succeeds for OpenClaw)
        """
        self._session_id = session_id
        return True

    def clear_session(self) -> None:
        """Clear the current session."""
        self._session_id = None
