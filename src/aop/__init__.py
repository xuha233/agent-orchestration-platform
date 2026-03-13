"""AOP - Agent Orchestration Platform."""

import tomllib
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError


def get_version() -> str:
    """获取版本号，优先从 pyproject.toml 读取（开发环境），fallback 到已安装包版本。"""
    # 优先从 pyproject.toml 读取（开发环境）
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                return data["project"]["version"]
        except (KeyError, Exception):
            pass
    
    # fallback 到已安装包的版本
    try:
        return version("agent-orchestration-platform")
    except PackageNotFoundError:
        return "0.5.0"  # 最终 fallback


__version__ = get_version()

__all__ = [
    "ComplexityAssessment",
    "Evidence",
    "Hypothesis",
    "HypothesisState",
    "LearningCapture",
    "NormalizedFinding",
    "ProjectType",
    "TaskInput",
    "TaskResult",
    "TaskState",
    "TeamConfig",
    "ExecutionEngine",
    "HypothesisManager",
    "LearningLog",
    "TeamOrchestrator",
    "AOPConfig",
    "load_config",
    "ReportGenerator",
]

from .core.types import (
    ComplexityAssessment,
    Evidence,
    Hypothesis,
    HypothesisState,
    LearningCapture,
    NormalizedFinding,
    ProjectType,
    TaskInput,
    TaskResult,
    TaskState,
    TeamConfig,
)
from .core.engine import ExecutionEngine
from .workflow.hypothesis import HypothesisManager
from .workflow.learning import LearningLog
from .workflow.team import TeamOrchestrator
from .config import AOPConfig, load_config
from .report import ReportGenerator
