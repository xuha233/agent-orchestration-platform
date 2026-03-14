"""Executor discovery and management."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict


class ExecutorType(Enum):
    """Supported executor types"""
    CLAUDE_CODE = "claude-code"
    OPENCODE = "opencode"
    CODEX = "codex"


@dataclass
class ExecutorInfo:
    """Executor information"""
    executor_type: ExecutorType
    available: bool
    binary_name: str = ""
    binary_path: str | None = None
    version: str | None = None
    error: str | None = None


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
        info = check_executor(executor_type)
        executors.append(info)
    return executors


def check_executor(executor_type: ExecutorType) -> ExecutorInfo:
    """Check if a specific executor is available."""
    config = EXECUTOR_CONFIGS.get(executor_type, {})
    binary_name = config.get("binary", executor_type.value)
    binary_path = shutil.which(binary_name)

    if not binary_path:
        return ExecutorInfo(
            executor_type=executor_type,
            available=False,
            binary_name=binary_name,
            error=f"Command '{binary_name}' not found in PATH",
        )

    # Try to get version
    version = None
    try:
        # On Windows, .cmd/.bat files need shell=True or full path execution
        # Check if this is a .cmd/.bat file on Windows
        use_shell = binary_path.lower().endswith(('.cmd', '.bat'))
        
        result = subprocess.run(
            [binary_name, "--version"] if not use_shell else f'"{binary_name}" --version',
            capture_output=True,
            text=True,
            timeout=5,
            shell=use_shell,
            encoding='utf-8',
            errors='replace',  # Handle any encoding issues gracefully
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0][:50]
    except FileNotFoundError:
        # Fallback: try with shell=True using full path
        try:
            result = subprocess.run(
                f'"{binary_path}" --version',
                capture_output=True,
                text=True,
                timeout=5,
                shell=True,
                encoding='utf-8',
                errors='replace',
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0][:50]
        except Exception:
            pass
    except Exception:
        pass

    return ExecutorInfo(
        executor_type=executor_type,
        available=True,
        binary_name=binary_name,
        binary_path=binary_path,
        version=version,
    )


def discover_all() -> Dict[ExecutorType, ExecutorInfo]:
    """Discover all executors and return as a dict."""
    return {info.executor_type: info for info in discover_executors()}


def get_available_executors() -> List[ExecutorType]:
    """Get list of available executor types."""
    return [info.executor_type for info in discover_executors() if info.available]


def get_best_executor() -> ExecutorType:
    """Get the best available executor (preference order: claude-code > opencode > codex)."""
    available = get_available_executors()
    for pref in [ExecutorType.CLAUDE_CODE, ExecutorType.OPENCODE, ExecutorType.CODEX]:
        if pref in available:
            return pref
    return ExecutorType.CLAUDE_CODE
