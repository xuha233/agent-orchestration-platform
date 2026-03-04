"""Agent registry for managing PrimaryAgent instances.

Provides a central registry for discovering and selecting available
primary agents.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import PrimaryAgent


class AgentRegistry:
    """Central registry for PrimaryAgent instances.

    The registry maintains a collection of available agents and provides
    methods to discover, register, and select agents based on availability.

    Example:
        >>> registry = AgentRegistry()
        >>> registry.register(ClaudeCodeAgent())
        >>> registry.register(OpenCodeAgent())
        >>> agent = registry.get_default()
        >>> if agent:
        ...     print(f"Using {agent.name}")
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._agents: Dict[str, PrimaryAgent] = {}

    def register(self, agent: PrimaryAgent) -> None:
        """Register an agent with the registry.

        Args:
            agent: The PrimaryAgent instance to register
        """
        self._agents[agent.id] = agent

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Args:
            agent_id: The ID of the agent to remove

        Returns:
            True if the agent was removed, False if it wasn't registered
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get(self, agent_id: str) -> Optional[PrimaryAgent]:
        """Get an agent by ID.

        Args:
            agent_id: The ID of the agent to retrieve

        Returns:
            The agent if found, None otherwise
        """
        return self._agents.get(agent_id)

    def list_all(self) -> List[PrimaryAgent]:
        """List all registered agents.

        Returns:
            List of all registered PrimaryAgent instances
        """
        return list(self._agents.values())

    def list_available(self) -> List[PrimaryAgent]:
        """List all available agents.

        An agent is considered available if is_available() returns True.

        Returns:
            List of available PrimaryAgent instances
        """
        return [agent for agent in self._agents.values() if agent.is_available()]

    def get_default(self) -> Optional[PrimaryAgent]:
        """Get the default agent.

        Priority order:
        1. openclaw (not implemented yet)
        2. claude_code
        3. opencode

        Returns:
            The first available agent in priority order, or None if none available
        """
        # Priority order for default agent selection
        priority_order = ["openclaw", "claude_code", "opencode"]

        for agent_id in priority_order:
            agent = self._agents.get(agent_id)
            if agent and agent.is_available():
                return agent

        return None

    def has_available(self) -> bool:
        """Check if any agent is available.

        Returns:
            True if at least one agent is available
        """
        return any(agent.is_available() for agent in self._agents.values())

    def count(self) -> int:
        """Get the total number of registered agents.

        Returns:
            Number of registered agents
        """
        return len(self._agents)

    def count_available(self) -> int:
        """Get the number of available agents.

        Returns:
            Number of available agents
        """
        return sum(1 for agent in self._agents.values() if agent.is_available())


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get the global agent registry.

    Creates the registry on first access and registers default agents.

    Returns:
        The global AgentRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = AgentRegistry()
        # Register default agents
        from .claude_code import ClaudeCodeAgent
        from .opencode import OpenCodeAgent

        _global_registry.register(ClaudeCodeAgent())
        _global_registry.register(OpenCodeAgent())

    return _global_registry


def reset_registry() -> None:
    """Reset the global registry.

    This is mainly useful for testing.
    """
    global _global_registry
    _global_registry = None
