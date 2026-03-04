"""Primary agent module for AOP.

This module provides the abstraction layer for primary AI agents,
allowing different agent implementations to be swapped via a registry.

Classes:
    AgentContext: Execution context for agent sessions
    PrimaryAgent: Abstract base class for primary agents
    ClaudeCodeAgent: Claude Code CLI implementation
    OpenCodeAgent: OpenCode CLI implementation
    AgentRegistry: Central registry for managing agents

Functions:
    get_registry: Get the global agent registry
    reset_registry: Reset the global registry (for testing)
"""

from .base import AgentContext, PrimaryAgent
from .claude_code import ClaudeCodeAgent
from .opencode import OpenCodeAgent
from .registry import AgentRegistry, get_registry, reset_registry

__all__ = [
    "AgentContext",
    "PrimaryAgent",
    "ClaudeCodeAgent",
    "OpenCodeAgent",
    "AgentRegistry",
    "get_registry",
    "reset_registry",
]
