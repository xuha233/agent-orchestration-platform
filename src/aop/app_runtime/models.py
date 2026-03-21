"""Models for the desktop app runtime bridge."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DesktopAppHealth:
    """Top-level health and environment summary for the desktop app."""

    version: str
    platform: str
    workspace_count: int
    available_agents: int
    available_providers: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopProjectSummary:
    """Project summary exposed to the desktop shell."""

    project_id: str
    name: str
    project_path: str
    primary_agent: str
    last_active: str
    session_id: Optional[str] = None
    latest_run_id: str = ""
    latest_run_status: str = ""
    latest_run_phase: str = ""
    latest_run_completion: str = ""
    needs_follow_up: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopProviderStatus:
    """Provider availability and setup state for onboarding surfaces."""

    provider_id: str
    label: str
    detected: bool
    auth_ok: bool
    binary_path: Optional[str]
    version: Optional[str]
    reason: str = ""
    install_commands: List[str] = field(default_factory=list)
    required_env_vars: List[str] = field(default_factory=list)
    configured_env_vars: List[str] = field(default_factory=list)
    missing_env_vars: List[str] = field(default_factory=list)
    stored_env_vars: Dict[str, str] = field(default_factory=dict)
    preferred: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopRunLaunchResult:
    """Result returned after launching a run from the desktop shell."""

    project_id: str
    sprint_id: str
    success: bool
    state: str
    summary: str
    next_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
