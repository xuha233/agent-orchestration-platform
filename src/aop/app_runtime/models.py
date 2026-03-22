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
    attention_tags: List[str] = field(default_factory=list)
    priority_rank: int = 0
    triage_summary: str = ""
    triage_evidence: List[str] = field(default_factory=list)

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
class DesktopInstallResult:
    """Result returned after attempting a provider dependency install."""

    provider_id: str
    command: str
    success: bool
    summary: str
    output: str = ""
    next_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopSetupCheck:
    """System dependency readiness shown in the desktop setup workspace."""

    check_id: str
    label: str
    detected: bool
    required: bool
    version: str = ""
    reason: str = ""
    install_hint: str = ""
    install_commands: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopSetupInstallResult:
    """Result returned after attempting a system dependency install."""

    check_id: str
    command: str
    success: bool
    summary: str
    output: str = ""
    next_steps: List[str] = field(default_factory=list)

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


@dataclass
class DesktopRunJob:
    """Asynchronous desktop run job persisted for polling."""

    job_id: str
    project_id: str
    prompt: str
    status: str
    created_at: str
    updated_at: str
    sprint_id: str = ""
    summary: str = ""
    state: str = ""
    next_steps: List[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopMemoryStatus:
    """Memory status exposed to the desktop shell."""

    project_id: str
    project_path: str
    enabled: bool
    global_enabled: bool
    project_enabled: bool
    backend: str
    mem0_available: bool
    current_backend: str
    total_memories: int
    legacy_entry_count: int = 0
    migration_ready: bool = False
    migration_issues: List[str] = field(default_factory=list)
    memory_sources: Dict[str, int] = field(default_factory=dict)
    init_error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopMemoryRecord:
    """Recent memory record exposed to the desktop shell."""

    memory_id: str
    content: str
    memory_type: str
    phase: str
    run_id: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopMemoryMigrationResult:
    """Result returned after migrating legacy project memory into mem0."""

    project_id: str
    dry_run: bool
    success: bool
    total_migrated: int
    source_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopMemorySettings:
    """Editable memory settings exposed to the desktop shell."""

    project_id: str
    global_enabled: bool
    project_enabled: bool
    effective_enabled: bool
    backend: str
    search_top_k: int
    search_threshold: float
    embedding_model: str
    embedding_dims: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
