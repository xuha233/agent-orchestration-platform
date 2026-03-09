"""Primary agent module for AOP.

This module provides the abstraction layer for primary AI agents,
allowing different agent implementations to be swapped via a registry.

Classes:
    AgentContext: Execution context for agent sessions
    PrimaryAgent: Abstract base class for primary agents
    ClaudeCodeAgent: Claude Code CLI implementation
    OpenCodeAgent: OpenCode CLI implementation
    OpenClawAgent: OpenClaw AI Assistant implementation
    AgentRegistry: Central registry for managing agents
    Workspace: Project workspace configuration
    WorkspaceManager: Workspace management
    CommandListener: Command file listener

Functions:
    get_registry: Get the global agent registry
    reset_registry: Reset the global registry (for testing)
    submit_command: Submit a command to the listener
"""

from .base import AgentContext, PrimaryAgent
from .claude_code import ClaudeCodeAgent
from .opencode import OpenCodeAgent
from .openclaw import OpenClawAgent
from .registry import AgentRegistry, get_registry, reset_registry
from .workspace import Workspace, WorkspaceManager
from .listener import CommandListener, get_listener, start_listener, stop_listener, submit_command

__all__ = [
    "AgentContext",
    "PrimaryAgent",
    "ClaudeCodeAgent",
    "OpenCodeAgent",
    "OpenClawAgent",
    "AgentRegistry",
    "get_registry",
    "reset_registry",
    "Workspace",
    "WorkspaceManager",
    "CommandListener",
    "get_listener",
    "start_listener",
    "stop_listener",
    "submit_command",
]
