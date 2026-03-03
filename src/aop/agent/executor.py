"""Executor discovery and management."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum
from typing import List


class ExecutorType(Enum):
    """Supported executor types"""
    CLAUDE_CODE = "claude-code"
    OPENCODE = "opencode"
    CODEX = "codex"


@dataclass
class ExecutorInfo:
    """Executor information"""
    executor_type: ExecutorType
    binary_name: str
    binary_path: str | None
    version: str | None
    available: bool


EXECUTOR_CONFIGS = {
    ExecutorType.CLAUDE_CODE: {
        "binary": "claude",
        "install_hint": "npm install -g @anthropic-ai/claude-code",
    },
    ExecutorType.OPENCODE: {
        "binary": "opencode",
        "install_hint": "npm install -g opencode",
    },
    ExecutorType.CODEX: {
        "binary": "codex",
        "install_hint": "pip install codex-cli",
    },
}


def discover_executors() -> List[ExecutorInfo]:
    """Discover available executors on the system."""
    executors = []
    for executor_type in ExecutorType:
        config = EXECUTOR_CONFIGS.get(executor_type, {})
        binary_name = config.get("binary", executor_type.value)
        binary_path = shutil.which(binary_name)
        executors.append(ExecutorInfo(
            executor_type=executor_type,
            binary_name=binary_name,
            binary_path=binary_path,
            version="installed" if binary_path else None,
            available=binary_path is not None,
        ))
    return executors


def get_available_executors() -> List[ExecutorType]:
    """Get list of available executor types."""
    return [info.executor_type for info in discover_executors() if info.available]


def get_default_executor() -> ExecutorType:
    """Get the default executor (first available)."""
    available = get_available_executors()
    for pref in [ExecutorType.CLAUDE_CODE, ExecutorType.OPENCODE, ExecutorType.CODEX]:
        if pref in available:
            return pref
    return ExecutorType.CLAUDE_CODE
