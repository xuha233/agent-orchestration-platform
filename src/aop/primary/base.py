"""PrimaryAgent abstract base class for AOP.

Defines the interface for primary AI agents that can be used as the main
agent in the AOP system. Supports session management and streaming chat.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional


@dataclass
class AgentContext:
    """Agent execution context.

    Attributes:
        workspace_path: The working directory for the agent
        session_id: Optional session ID to resume a previous session
        history: Optional conversation history
    """

    workspace_path: Path
    session_id: Optional[str] = None
    history: list = field(default_factory=list)


class PrimaryAgent(ABC):
    """Abstract base class for primary AI agents.

    A primary agent is an AI assistant that can be used as the main
    conversational partner in the AOP system. Different implementations
    can be swapped via the registry.

    Attributes:
        id: Unique identifier for this agent type
        name: Human-readable name
        description: Brief description of this agent
    """

    id: str
    name: str
    description: str

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this agent is available on the current system.

        This should check for:
        - CLI binary availability
        - Authentication status
        - Any other prerequisites

        Returns:
            True if the agent can be used, False otherwise
        """
        pass

    @abstractmethod
    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        """Chat with the agent.

        This method is async and returns the complete response string.
        For streaming behavior, implementations may provide additional methods.

        Args:
            message: The user message to send
            context: Execution context with workspace and session info
            stream: Whether to stream the response (default True)

        Returns:
            Complete response text
        """
        pass

    @abstractmethod
    def get_session_id(self) -> Optional[str]:
        """Get the current session ID.

        Returns:
            The current session ID if one is active, None otherwise
        """
        pass

    @abstractmethod
    def resume_session(self, session_id: str) -> bool:
        """Resume a previous session.

        Args:
            session_id: The session ID to resume

        Returns:
            True if the session was successfully resumed, False otherwise
        """
        pass

    @abstractmethod
    def clear_session(self) -> None:
        """Clear the current session.

        This should reset the agent to a fresh state without any
        previous conversation context.
        """
        pass
